#include "user_config.h"
#include "lvgl_port.h"
#include "lcd_bl_pwm_bsp.h"
#include "network.h"

void setup()
{
    Serial.begin(115200);
    rackstats_network_start();
    lvgl_port_init(); // Patched port creates rackstats_ui_create() under its LVGL mutex.
    lcd_bl_pwm_bsp_init(LCD_PWM_MODE_255);
}

void loop()
{
    delay(10); // The port owns LVGL's tick/handler; the network worker owns HTTP.
}
