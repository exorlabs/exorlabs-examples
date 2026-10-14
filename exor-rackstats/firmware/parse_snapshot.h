#pragma once
#include <ArduinoJson.h>
#include <math.h>
#include <stdio.h>
#include <string.h>
#include "model.h"

static inline float stats_number(JsonVariantConst value)
{
    if(value.isNull() || value.is<bool>() || !(value.is<double>() || value.is<int64_t>())) return NAN;
    double number = value.as<double>();
    return isfinite(number) ? (float)number : NAN;
}

static inline float stats_percentage(JsonVariantConst value)
{
    float number=stats_number(value);
    return isfinite(number)&&number>=0&&number<=100?number:NAN;
}

static inline bool stats_parse(const char *body, const char *expected_source,
                               uint32_t now_ms, StatsSnapshot *out)
{
    JsonDocument doc;
    DeserializationError error = deserializeJson(doc, body);
    if(error || !doc["schema_version"].is<int>() || doc["schema_version"].is<bool>() || doc["schema_version"].as<int>() != 1 ||
       strcmp(doc["source"] | "", expected_source) != 0 || !doc["host"].is<JsonObject>()) return false;
    const char *state = doc["state"] | "";
    if(strcmp(state, "fresh") != 0 && strcmp(state, "stale") != 0) return false;
    const float age = stats_number(doc["age_seconds"]);
    if(!isfinite(age) || age < 0 || age > 1000000000) return false;
    StatsSnapshot s = {};
    s.valid = true;
    s.stale = strcmp(state, "stale") == 0;
    s.age_seconds = (uint32_t)age;
    s.received_at_ms = now_ms;
    snprintf(s.name, sizeof(s.name), "%s", doc["host"]["name"] | expected_source);
    snprintf(s.status, sizeof(s.status), "%s", s.stale ? "STALE" : "LIVE");
    s.cpu_percent = stats_percentage(doc["host"]["cpu_percent"]);
    s.memory_percent = stats_percentage(doc["host"]["memory"]["percent"]);
    s.storage_percent = stats_percentage(doc["host"]["storage"]["percent"]);
    s.temperature_c = stats_number(doc["host"]["temperature_c"]);
    s.rx_bytes_per_second = stats_number(doc["host"]["network"]["rx_bytes_per_second"]);
    s.tx_bytes_per_second = stats_number(doc["host"]["network"]["tx_bytes_per_second"]);
    s.vm_total = doc["vm_summary"]["total"].isNull() ? -1 : doc["vm_summary"]["total"].as<int>();
    s.vm_running = doc["vm_summary"]["running"].isNull() ? -1 : doc["vm_summary"]["running"].as<int>();
    for(JsonVariantConst warning : doc["warnings"].as<JsonArrayConst>())
        if(strcmp(warning | "", "simulated_data") == 0) s.simulated = true;
    *out = s;
    return true;
}
