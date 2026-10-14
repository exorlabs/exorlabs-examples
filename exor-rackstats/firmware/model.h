#ifndef EXOR_STATS_MODEL_H
#define EXOR_STATS_MODEL_H
#include <stdbool.h>
#include <stdint.h>
typedef struct {
    bool valid;
    bool stale;
    bool simulated;
    uint32_t age_seconds;
    uint32_t received_at_ms;
    float cpu_percent, memory_percent, storage_percent, temperature_c;
    float rx_bytes_per_second, tx_bytes_per_second;
    int vm_total, vm_running;
    char name[40];
    char status[40];
} StatsSnapshot;
typedef struct { StatsSnapshot sources[2]; } StatsPair;
#ifdef __cplusplus
extern "C" {
#endif
bool rackstats_take_snapshot(StatsPair *pair);
uint32_t rackstats_now_ms(void);
void rackstats_ui_create(void);
#ifdef __cplusplus
}
#endif
#endif
