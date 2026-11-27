// HP60C SDK -> Windows named shared memory bridge
//
// Based on shm_bridge.cpp from th2102da/hp60c-camera
//   MIT License, Copyright (c) 2026 hp60c_camera contributors
//   (Permission is hereby granted ... — 전체 문구는 원 저장소 LICENSE 참고)
// 제조사 SDK(헤더·DLL)는 Angstrong 독점 라이선스라 이 저장소에 넣지 않는다. README 참고.
//
// th2102da/hp60c-camera 의 Linux shm_bridge.cpp 를 Windows 로 옮긴 것.
// - POSIX shm(/dev/shm) 대신 Windows 이름 있는 공유 메모리 "Local\hp60c_frames"
// - dirent 대신 std::filesystem
// - SDK: Angstrong Viewer 에 들어 있는 AngstrongCameraSdk.dll (x64, MSVC)
//
// 메모리 레이아웃은 Linux 판과 같다 (Python reader 를 그대로 맞춤):
//   [Header 64 bytes] magic "HP60", rgb_w/h/size, depth_w/h/size, seq(쓰기 순번),
//                     frame_id(u64), timestamp_us(u64), rgb_ready, depth_ready
//   [RGB   : 1920*1080*3 bytes, BGR uint8]
//   [Depth : 640*480*2  bytes, uint16 mm]
//
// 사용법: hp60c_bridge.exe <configurationfiles 폴더>

#define WIN32_LEAN_AND_MEAN
#include <windows.h>

#include <atomic>
#include <chrono>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <filesystem>
#include <list>
#include <string>
#include <thread>
#include <vector>

#include "as_camera_sdk_api.h"
#include "as_camera_sdk_def.h"

namespace fs = std::filesystem;

#define SHM_NAME        "Local\\hp60c_frames"
#define HEADER_SIZE     64
#define MAX_RGB_SIZE    (1920 * 1080 * 3)
#define MAX_DEPTH_SIZE  (640 * 480 * 2)
#define SHM_TOTAL_SIZE  (HEADER_SIZE + MAX_RGB_SIZE + MAX_DEPTH_SIZE)
#define SHM_MAGIC       0x48503630u  // "HP60"

struct ShmHeader {
    uint32_t magic;
    uint32_t rgb_w, rgb_h, rgb_size;
    uint32_t depth_w, depth_h, depth_size;
    uint32_t seq;  // 쓰기 순번: 홀수 = 쓰는 중, 짝수 = 완료 (Linux 판의 _pad 자리, 읽는 쪽이 섞인 프레임을 거름)
    uint64_t frame_id;
    uint64_t timestamp_us;
    uint32_t rgb_ready;
    uint32_t depth_ready;
};
static_assert(sizeof(ShmHeader) <= HEADER_SIZE, "header too big");

static std::atomic<bool> g_running{true};
static uint8_t* g_shm_ptr = nullptr;
static uint64_t g_frame_id = 0;
static AS_CAM_PTR g_camera = nullptr;
static std::string g_config_dir;
static std::atomic<uint64_t> g_cb_count{0};

static BOOL WINAPI ctrl_handler(DWORD) { g_running = false; return TRUE; }

static std::string findConfigFile(const std::string& dir, const std::string& key) {
    std::error_code ec;
    for (auto& e : fs::recursive_directory_iterator(dir, ec)) {
        if (!e.is_regular_file()) continue;
        std::string name = e.path().filename().string();
        if (name.find(key) != std::string::npos) return e.path().string();
    }
    return "";
}

static void onNewFrame(AS_CAM_PTR, const AS_SDK_Data_s* d, void*) {
    if (!g_shm_ptr || !g_running || !d) return;
    auto* hdr = reinterpret_cast<ShmHeader*>(g_shm_ptr);
    uint8_t* rgb = g_shm_ptr + HEADER_SIZE;
    uint8_t* depth = g_shm_ptr + HEADER_SIZE + MAX_RGB_SIZE;

    if (g_cb_count++ == 0) {  // 첫 프레임 정보는 화면에 한 번 찍어 둔다 (헤더·DLL 버전 차이 확인용)
        printf("[bridge] first frame: rgb %ux%u size=%u, depth %ux%u size=%u, ir %ux%u\n",
               d->rgbImg.width, d->rgbImg.height, d->rgbImg.size,
               d->depthImg.width, d->depthImg.height, d->depthImg.size,
               d->irImg.width, d->irImg.height);
        fflush(stdout);
    }

    g_frame_id++;
    // seqlock: 쓰기 전에 홀수로, 다 쓴 뒤 짝수로. 읽는 쪽은 앞뒤 seq 가 같고 짝수일 때만 받아들인다.
    auto* seq = reinterpret_cast<volatile LONG*>(&hdr->seq);
    InterlockedIncrement(seq);  // 홀수: 쓰는 중 (전체 메모리 장벽 포함)
    if (d->rgbImg.data && d->rgbImg.size > 0 && d->rgbImg.size <= MAX_RGB_SIZE) {
        hdr->rgb_w = d->rgbImg.width;
        hdr->rgb_h = d->rgbImg.height;
        hdr->rgb_size = d->rgbImg.size;
        memcpy(rgb, d->rgbImg.data, d->rgbImg.size);
        hdr->rgb_ready = 1;
    }
    if (d->depthImg.data && d->depthImg.size > 0 && d->depthImg.size <= MAX_DEPTH_SIZE) {
        hdr->depth_w = d->depthImg.width;
        hdr->depth_h = d->depthImg.height;
        hdr->depth_size = d->depthImg.size;
        memcpy(depth, d->depthImg.data, d->depthImg.size);
        hdr->depth_ready = 1;
    }
    hdr->frame_id = g_frame_id;
    hdr->timestamp_us = std::chrono::duration_cast<std::chrono::microseconds>(
        std::chrono::steady_clock::now().time_since_epoch()).count();
    hdr->magic = SHM_MAGIC;
    InterlockedIncrement(seq);  // 짝수: 완료
}

static void startCamera(AS_CAM_PTR cam);

static void onAttached(AS_CAM_ATTR_S* attr, void*) {
    printf("[bridge] onAttached\n");
    if (g_camera) return;
    AS_CAM_PTR cam = nullptr;
    if (AS_SDK_CreateCamHandle(cam, attr) != 0) {
        fprintf(stderr, "[bridge] CreateCamHandle failed\n");
        return;
    }
    startCamera(cam);
}

static void startCamera(AS_CAM_PTR cam) {
    AS_SDK_CAM_MODEL_E model;
    AS_SDK_GetCameraModel(cam, model);
    printf("[bridge] Camera attached, model type: %d (HP60C = %d)\n", model, AS_SDK_CAM_MODEL_HP60C);

    std::string cfg = findConfigFile(g_config_dir, "hp60c_");
    if (cfg.empty()) cfg = findConfigFile(g_config_dir, "nuwa_");
    if (cfg.empty()) {
        fprintf(stderr, "[bridge] No config file in %s\n", g_config_dir.c_str());
        return;
    }
    printf("[bridge] Using config: %s\n", cfg.c_str());
    if (AS_SDK_OpenCamera(cam, cfg.c_str()) != 0) {
        fprintf(stderr, "[bridge] OpenCamera failed\n");
        return;
    }

    AS_CAM_Parameter_s p{};
    if (AS_SDK_GetCamParameter(cam, &p) == 0) {
        printf("[bridge] IR : fx=%.1f fy=%.1f cx=%.1f cy=%.1f\n", p.fxir, p.fyir, p.cxir, p.cyir);
        printf("[bridge] RGB: fx=%.1f fy=%.1f cx=%.1f cy=%.1f\n", p.fxrgb, p.fyrgb, p.cxrgb, p.cyrgb);
        if (FILE* fp = fopen("hp60c_params.txt", "w")) {
            fprintf(fp, "fxir=%.6f\nfyir=%.6f\ncxir=%.6f\ncyir=%.6f\n", p.fxir, p.fyir, p.cxir, p.cyir);
            fprintf(fp, "fxrgb=%.6f\nfyrgb=%.6f\ncxrgb=%.6f\ncyrgb=%.6f\n", p.fxrgb, p.fyrgb, p.cxrgb, p.cyrgb);
            fprintf(fp, "T1=%.6f\nT2=%.6f\nT3=%.6f\n", p.T1, p.T2, p.T3);
            fclose(fp);
        }
    }

    AS_CAM_Stream_Cb_s cb{};
    cb.callback = onNewFrame;
    cb.privateData = nullptr;
    AS_SDK_RegisterStreamCallback(cam, &cb);
    if (AS_SDK_StartStream(cam) != 0) {
        fprintf(stderr, "[bridge] StartStream failed\n");
        return;
    }
    g_camera = cam;
    printf("[bridge] Streaming started. (Ctrl+C to stop)\n");
    fflush(stdout);
}

static void onDetached(AS_CAM_ATTR_S*, void*) {
    printf("[bridge] Camera detached\n");
    if (g_camera) {
        AS_SDK_StopStream(g_camera);
        AS_SDK_CloseCamera(g_camera);
        AS_SDK_DestoryCamHandle(g_camera);
        g_camera = nullptr;
    }
}

int main(int argc, char* argv[]) {
    SetConsoleCtrlHandler(ctrl_handler, TRUE);
    setvbuf(stdout, nullptr, _IONBF, 0);  // 파이프로 실행해도 메시지가 바로 보이게
    g_config_dir = argc > 1 ? argv[1] : "configurationfiles";
    printf("[bridge] Config dir: %s\n", g_config_dir.c_str());

    HANDLE hmap = CreateFileMappingA(INVALID_HANDLE_VALUE, nullptr, PAGE_READWRITE, 0,
                                     SHM_TOTAL_SIZE, SHM_NAME);
    if (!hmap) { fprintf(stderr, "[bridge] CreateFileMapping failed: %lu\n", GetLastError()); return 1; }
    g_shm_ptr = static_cast<uint8_t*>(MapViewOfFile(hmap, FILE_MAP_ALL_ACCESS, 0, 0, SHM_TOTAL_SIZE));
    if (!g_shm_ptr) { fprintf(stderr, "[bridge] MapViewOfFile failed: %lu\n", GetLastError()); return 1; }
    memset(g_shm_ptr, 0, SHM_TOTAL_SIZE);
    printf("[bridge] Shared memory ready: %s (%d bytes)\n", SHM_NAME, SHM_TOTAL_SIZE);

    if (AS_SDK_Init() != 0) { fprintf(stderr, "[bridge] AS_SDK_Init failed\n"); return 1; }
    printf("[bridge] SDK initialized. Waiting for camera...\n");
    fflush(stdout);

    AS_LISTENER_CALLBACK_S listener{};
    listener.onAttached = onAttached;
    listener.onDetached = onDetached;
    listener.privateData = nullptr;
    AS_SDK_StartListener(listener, AS_LISTENNER_TYPE_USB, true);

    // Windows SDK 는 이미 꽂혀 있는 카메라에 대해 onAttached 를 안 부를 때가 있어(11/27 확인) 목록에서 직접 연다
    std::this_thread::sleep_for(std::chrono::seconds(2));
    if (!g_camera) {
        std::list<AS_CAM_PTR> devs;
        int rc = AS_SDK_GetCameraList(devs);
        printf("[bridge] GetCameraList rc=%d, %zu camera(s)\n", rc, devs.size());
        if (!devs.empty()) startCamera(devs.front());
    }

    uint64_t last = 0;
    auto t0 = std::chrono::steady_clock::now();
    while (g_running) {
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
        auto now = std::chrono::steady_clock::now();
        if (now - t0 >= std::chrono::seconds(5)) {  // 5초마다 fps 한 줄
            uint64_t n = g_cb_count.load();
            printf("[bridge] %.1f fps\n", (n - last) / 5.0);
            fflush(stdout);
            last = n;
            t0 = now;
        }
    }

    printf("\n[bridge] Stopping...\n");
    if (g_camera) {
        AS_SDK_StopStream(g_camera);
        AS_SDK_CloseCamera(g_camera);
        AS_SDK_DestoryCamHandle(g_camera);
    }
    AS_SDK_StopListener();
    AS_SDK_Deinit();
    UnmapViewOfFile(g_shm_ptr);
    CloseHandle(hmap);
    printf("[bridge] Done.\n");
    return 0;
}
