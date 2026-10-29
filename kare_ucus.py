import math
import csv
import time

from pymavlink import mavutil

BAGLANTI = "udp:127.0.0.1:14550"
IRTIFA = 10.0
KENAR = 20.0


def mod_ayarla(iha, mod):
    iha.set_mode(mod)
    while iha.flightmode != mod:
        iha.recv_match(type="HEARTBEAT", blocking=True, timeout=1)


def konuma_git(iha, kuzey, dogu, asagi):
    iha.mav.set_position_target_local_ned_send(
        0, iha.target_system, iha.target_component,
        mavutil.mavlink.MAV_FRAME_LOCAL_NED,
        0b110111111000,
        kuzey, dogu, asagi, 0, 0, 0, 0, 0, 0, 0, 0)


def kayit_al(iha, yazici, baslangic):
    msg = iha.recv_match(type="GLOBAL_POSITION_INT", blocking=True, timeout=1)
    if msg is None:
        return None
    irtifa = msg.relative_alt / 1000.0
    yazici.writerow([round(time.time() - baslangic, 2),
                     msg.lat / 1e7, msg.lon / 1e7, irtifa])
    return irtifa


def main():
    iha = mavutil.mavlink_connection(BAGLANTI)
    iha.wait_heartbeat()
    iha.mav.request_data_stream_send(iha.target_system, iha.target_component,
                                     mavutil.mavlink.MAV_DATA_STREAM_ALL, 10, 1)
    print("Bağlandı: sistem", iha.target_system)

    with open("ucus_kaydi.csv", "w", newline="") as f:
        yazici = csv.writer(f)
        yazici.writerow(["zaman_s", "enlem", "boylam", "irtifa_m"])
        baslangic = time.time()

        mod_ayarla(iha, "GUIDED")
        while not iha.motors_armed():
            iha.arducopter_arm()
            iha.recv_match(type="HEARTBEAT", blocking=True, timeout=2)
            time.sleep(2)
        print("Motorlar açık")

        iha.mav.command_long_send(
            iha.target_system, iha.target_component,
            mavutil.mavlink.MAV_CMD_NAV_TAKEOFF, 0, 0, 0, 0, 0, 0, 0, IRTIFA)

        debut = time.time()
        while time.time() - debut < 40:
            irtifa = kayit_al(iha, yazici, baslangic)
            if irtifa is not None and irtifa >= IRTIFA * 0.95:
                break
        else:
            print("Zaman aşımı: irtifa alınamadı")
            return
        print("Irtifa tamam")

        koseler = [(KENAR, 0), (KENAR, KENAR), (0, KENAR), (0, 0)]
        for kuzey, dogu in koseler:
            debut = time.time()
            while time.time() - debut < 60:
                konuma_git(iha, kuzey, dogu, -IRTIFA)
                kayit_al(iha, yazici, baslangic)
                konum = iha.recv_match(type="LOCAL_POSITION_NED", blocking=True, timeout=1)
                if konum and math.hypot(konum.x - kuzey, konum.y - dogu) < 1.0:
                    break
            print("Köşeye ulaşıldı:", kuzey, dogu)

        mod_ayarla(iha, "LAND")
        debut = time.time()
        while time.time() - debut < 60:
            irtifa = kayit_al(iha, yazici, baslangic)
            if irtifa is not None and irtifa < 0.3:
                break
        print("İniş tamam, kayıt: ucus_kaydi.csv")


if __name__ == "__main__":
    main()
