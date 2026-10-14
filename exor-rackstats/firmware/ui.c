#include "lvgl.h"
#include "model.h"
#include <math.h>
#include <stdio.h>

#if LVGL_VERSION_MAJOR != 9
#error "ExorRackStats requires LVGL 9"
#endif

static StatsPair latest;
static lv_obj_t *heading, *connection, *cpu_value, *memory_value, *disk_value;
static lv_obj_t *cpu_bar, *memory_bar, *disk_bar, *footer;
static bool initialized;

static lv_color_t load_color(float v, bool disk)
{
    float low=disk?75:25, high=disk?90:70;
    return lv_color_hex(v<low?0x22c55e:v<=high?0xf59e0b:0xef4444);
}

static void metric(lv_obj_t *value, lv_obj_t *bar, float number, bool disk)
{
    if(!isfinite(number)) {
        lv_label_set_text(value,"--");
        lv_bar_set_value(bar,0,LV_ANIM_OFF);
        lv_obj_set_style_text_color(value,lv_color_hex(0x94a3b8),LV_PART_MAIN);
        return;
    }
    lv_color_t color=load_color(number,disk);
    char text[24];snprintf(text,sizeof(text),"%.0f%%",(double)number);
    lv_label_set_text(value,text);
    lv_bar_set_value(bar,(int32_t)number,LV_ANIM_OFF);
    lv_obj_set_style_text_color(value,color,LV_PART_MAIN);
    lv_obj_set_style_bg_color(bar,color,LV_PART_INDICATOR);
}

static void update(lv_timer_t *timer)
{
    (void)timer;
    rackstats_take_snapshot(&latest);
    uint32_t now=rackstats_now_ms();
    unsigned index=(now/10000u)%2u;
    StatsSnapshot *s=&latest.sources[index];
    uint32_t age=s->age_seconds+(uint32_t)(now-s->received_at_ms)/1000u;
    bool stale=s->stale||age>20;
    char heading_text[80], connection_text[160];
    snprintf(heading_text,sizeof(heading_text),"%s | EXOR LABS",s->name[0]?s->name:(index==0?"Synology":"Proxmox"));
    lv_label_set_text(heading,heading_text);
    if(!s->valid)snprintf(connection_text,sizeof(connection_text),"OFFLINE | %s",s->status[0]?s->status:"Waiting for data");
    else snprintf(connection_text,sizeof(connection_text),"%s%s | age %lu s | %s",s->simulated?"DEMO / ":"",stale?"STALE":"LIVE",(unsigned long)age,s->status);
    lv_label_set_text(connection,connection_text);
    lv_obj_set_style_text_color(connection,lv_color_hex(!s->valid||stale?0xf59e0b:0x22c55e),LV_PART_MAIN);
    metric(cpu_value,cpu_bar,s->valid?s->cpu_percent:NAN,false);
    metric(memory_value,memory_bar,s->valid?s->memory_percent:NAN,false);
    metric(disk_value,disk_bar,s->valid?s->storage_percent:NAN,true);
    char rx[20]="--",tx[20]="--",temperature[16]="--",vms[24]="--";
    if(s->valid&&isfinite(s->rx_bytes_per_second))snprintf(rx,sizeof(rx),"%.1f",(double)s->rx_bytes_per_second/1024);
    if(s->valid&&isfinite(s->tx_bytes_per_second))snprintf(tx,sizeof(tx),"%.1f",(double)s->tx_bytes_per_second/1024);
    if(s->valid&&isfinite(s->temperature_c))snprintf(temperature,sizeof(temperature),"%.0f C",(double)s->temperature_c);
    if(s->valid&&s->vm_total>=0)snprintf(vms,sizeof(vms),"%d/%d",s->vm_running,s->vm_total);
    char footer_text[160];
    snprintf(footer_text,sizeof(footer_text),"RX %s / TX %s KiB/s | Temp %s | VMs %s",rx,tx,temperature,vms);
    lv_label_set_text(footer,footer_text);
}

static void card(lv_obj_t *screen,const char *title,int32_t x,int32_t y,int32_t w,int32_t h,lv_obj_t **value,lv_obj_t **bar)
{
    lv_obj_t *panel=lv_obj_create(screen);
    lv_obj_set_pos(panel,x,y);lv_obj_set_size(panel,w,h);
    lv_obj_remove_flag(panel,LV_OBJ_FLAG_SCROLLABLE);
    lv_obj_set_style_pad_all(panel,16,LV_PART_MAIN);
    lv_obj_set_style_radius(panel,12,LV_PART_MAIN);
    lv_obj_set_style_border_color(panel,lv_color_hex(0x334155),LV_PART_MAIN);
    lv_obj_set_style_bg_color(panel,lv_color_hex(0x17243b),LV_PART_MAIN);
    lv_obj_t *caption=lv_label_create(panel);lv_label_set_text(caption,title);
    lv_obj_set_style_text_color(caption,lv_color_hex(0x94a3b8),LV_PART_MAIN);
    *value=lv_label_create(panel);lv_obj_set_pos(*value,0,36);
#if LV_FONT_MONTSERRAT_32
    lv_obj_set_style_text_font(*value,&lv_font_montserrat_32,LV_PART_MAIN);
#endif
    *bar=lv_bar_create(panel);lv_obj_set_size(*bar,w-34,12);
    lv_obj_align(*bar,LV_ALIGN_BOTTOM_LEFT,0,-12);lv_bar_set_range(*bar,0,100);
    lv_obj_set_style_bg_color(*bar,lv_color_hex(0x334155),LV_PART_MAIN);
}

void rackstats_ui_create(void)
{
    if(initialized)return;
    initialized=true;
    lv_obj_t *screen=lv_screen_active();
    int32_t w=lv_display_get_horizontal_resolution(lv_display_get_default());
    int32_t h=lv_display_get_vertical_resolution(lv_display_get_default());
    bool landscape=w>h;
    lv_obj_set_style_bg_color(screen,lv_color_hex(0x0b1220),LV_PART_MAIN);
    lv_obj_set_style_pad_all(screen,0,LV_PART_MAIN);lv_obj_remove_flag(screen,LV_OBJ_FLAG_SCROLLABLE);
    heading=lv_label_create(screen);lv_obj_set_pos(heading,16,14);lv_obj_set_width(heading,w-32);
    lv_label_set_long_mode(heading,LV_LABEL_LONG_DOT);
    lv_obj_set_style_text_color(heading,lv_color_hex(0xf8fafc),LV_PART_MAIN);
#if LV_FONT_MONTSERRAT_24
    lv_obj_set_style_text_font(heading,&lv_font_montserrat_24,LV_PART_MAIN);
#endif
    connection=lv_label_create(screen);lv_obj_set_pos(connection,16,46);lv_obj_set_width(connection,w-32);
    lv_label_set_long_mode(connection,LV_LABEL_LONG_DOT);
    int32_t cw=landscape?(w-56)/3:w-32,ch=landscape?h-120:(h-150)/3;
    int32_t dx=landscape?cw+12:0,dy=landscape?0:ch+12;
    card(screen,"CPU LOAD",16,78,cw,ch,&cpu_value,&cpu_bar);
    card(screen,"MEMORY USED",16+dx,78+dy,cw,ch,&memory_value,&memory_bar);
    card(screen,"FILESYSTEM USED",16+dx*2,78+dy*2,cw,ch,&disk_value,&disk_bar);
    footer=lv_label_create(screen);lv_obj_set_width(footer,w-32);lv_label_set_long_mode(footer,LV_LABEL_LONG_DOT);
    lv_obj_align(footer,LV_ALIGN_BOTTOM_LEFT,16,-14);lv_obj_set_style_text_color(footer,lv_color_hex(0x94a3b8),LV_PART_MAIN);
    update(NULL);
    LV_ASSERT_NULL(lv_timer_create(update,1000,NULL));
}
