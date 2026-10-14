#include <Arduino.h>
#include <HTTPClient.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <time.h>
#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"
#include "freertos/task.h"
#include "config.h"
#include "model.h"
#include "network.h"
#include "parse_snapshot.h"

static QueueHandle_t snapshots;
static StatsPair current;

extern "C" uint32_t rackstats_now_ms(void) { return millis(); }
extern "C" bool rackstats_take_snapshot(StatsPair *pair)
{
    return snapshots && xQueueReceive(snapshots, pair, 0) == pdTRUE;
}

static bool request_stats(const char *url, const char *token, const char *source, StatsSnapshot *out)
{
    bool tls = strncmp(url, "https://", 8) == 0;
    if(!tls && (!ALLOW_LAN_HTTP || strncmp(url, "http://", 7) != 0)) {
        snprintf(out->status, sizeof(out->status), "HTTP disabled"); out->stale = true; return false;
    }
    if(tls && strstr(STATS_CA_PEM, "BEGIN CERTIFICATE") == nullptr) {
        snprintf(out->status, sizeof(out->status), "Missing TLS CA"); out->stale = true; return false;
    }
    if(tls && time(nullptr) < 1700000000) {
        snprintf(out->status, sizeof(out->status), "Waiting for clock"); out->stale = true; return false;
    }
    HTTPClient http;
    WiFiClient plain;
    WiFiClientSecure secure;
    if(tls) secure.setCACert(STATS_CA_PEM);
    bool begun = tls ? http.begin(secure, url) : http.begin(plain, url);
    if(!begun) { snprintf(out->status, sizeof(out->status), "Invalid URL"); out->stale = true; return false; }
    http.setConnectTimeout(2500);
    http.setTimeout(3000);
    http.setFollowRedirects(HTTPC_DISABLE_FOLLOW_REDIRECTS);
    http.addHeader("Authorization", String("Bearer ") + token);
    int code = http.GET();
    bool ok = false;
    if(code == 200 && http.getSize() >= 0 && http.getSize() <= 16384) {
        String body = http.getString();
        ok = body.length() <= 16384 && stats_parse(body.c_str(), source, millis(), out);
    }
    if(!ok) { snprintf(out->status, sizeof(out->status), "Fetch failed (%d)", code); out->stale = true; }
    http.end();
    return ok;
}

static void worker(void *)
{
    WiFi.mode(WIFI_STA);
    WiFi.setAutoReconnect(true);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    configTime(0, 0, NTP_SERVER);
    for(;;) {
        if(WiFi.status() == WL_CONNECTED) {
            request_stats(NAS_STATS_URL, NAS_STATS_TOKEN, "nas", &current.sources[0]);
            xQueueOverwrite(snapshots, &current);
            request_stats(PROXMOX_STATS_URL, PROXMOX_STATS_TOKEN, "proxmox", &current.sources[1]);
        } else {
            for(auto &s : current.sources) { s.stale = true; snprintf(s.status, sizeof(s.status), "Wi-Fi offline"); }
        }
        xQueueOverwrite(snapshots, &current);
        vTaskDelay(pdMS_TO_TICKS(POLL_MS));
    }
}

void rackstats_network_start(void)
{
    snapshots = xQueueCreate(1, sizeof(StatsPair));
    configASSERT(snapshots);
    for(unsigned i=0;i<2;++i) {
        auto &s=current.sources[i];
        s.cpu_percent=s.memory_percent=s.storage_percent=s.temperature_c=NAN;
        s.rx_bytes_per_second=s.tx_bytes_per_second=NAN;
        s.vm_total=s.vm_running=-1;
        snprintf(s.name,sizeof(s.name),"%s",i==0?"Synology":"Proxmox");
        snprintf(s.status,sizeof(s.status),"Waiting for data");
    }
    xQueueOverwrite(snapshots, &current);
    BaseType_t started = xTaskCreatePinnedToCore(worker, "stats-network", 12288, nullptr, 2, nullptr, 0);
    configASSERT(started == pdPASS);
}
