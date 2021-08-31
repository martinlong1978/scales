import board
import pwmio
import time
import ssl
import socketpool
import wifi
import adafruit_dotstar
import adafruit_minimqtt.adafruit_minimqtt as MQTT
import displayio
import digitalio
import busio
import terminalio
import adafruit_requests as requests
import supervisor
import array
import countio
from adafruit_bitmap_font import bitmap_font
import ads123x
import alarm
#import traceback

from adafruit_display_text import label
import adafruit_displayio_sh1107


font = bitmap_font.load_font("/fonts/Anton-Regular-32.bdf")
smallfont = terminalio.FONT #bitmap_font.load_font("/fonts/ArchivoNarrow-Bold-12.bdf")

def setdisplay():
    global display
    displayio.release_displays()

    # Use for I2C
    i2c = board.I2C()
    display_bus = displayio.I2CDisplay(i2c, device_address=0x3C) 

    # SH1107 is vertically oriented 64x128
    WIDTH = 128
    HEIGHT = 64
    BORDER = 2

    display = adafruit_displayio_sh1107.SH1107(
        display_bus, width=WIDTH, height=HEIGHT, rotation=0
    )

class MultiTare :

    def __init__(self, loadcells):
        self.loadcells = loadcells
        self.name = "Multple Tare"


    def init(self):
        splash = displayio.Group()
        display.show(splash)
        self.tares = 6
        self.tarevalues = [0.0] * self.tares
        self.active = 0
        self.weight = 0
        self.status = ads123x.STATUS_TARE
        self.tarecache = None

        #trs = [f' {x+1} ' for x in range(0, self.tares)]
        self.tare_area = label.Label(smallfont, text='', color=0xFFFFFF, x=10, y=4)
        self.text_area = label.Label(font, text='', color=0xFFFFFF, x=10, y=30)
        self.status_area = label.Label(smallfont, text='', color=0xFFFFFF, x=10, y=56)
        splash.append(self.text_area)
        splash.append(self.tare_area)
        splash.append(self.status_area)
        self.refresh()


    def refresh(self) :
        self.updatetares()
        if self.status == ads123x.STATUS_TARE :
            self.text_area.text = '---'
            self.status_area.text = 'TARE'        
            return
        if status == ads123x.STATUS_SETTLE :
            self.status_area.text = 'WAIT'
            return        
        self.status_area.text = ''
        val = self.weight - self.gettarevalue()
        text1 = f"{round(val / 1000, 3)}kg" if val >= 1000 else f"{val}g"  
        self.text_area.text = text1
    
    def updatetares(self):
        trs = [(f'[{x+1}]' if x == self.active else f' {x+1} ') for x in range(0, self.tares)]
        tarelist = ''.join(trs)
        self.tare_area.text = tarelist

    def gettarevalue(self) :
        if self.tarecache == None :
            self.tarecache = sum(self.tarevalues) - self.tarevalues[self.active]
        return self.tarecache

    def showweight(self, weight, status):
        self.status = status
        if status == ads123x.STATUS_OK:
            self.weight = round(weight, 1)
        self.refresh()

    def btn_a(self) :
        self.tarevalues[self.active] = self.weight - self.gettarevalue()
        self.active = (self.active + 1) % 6
        self.tarecache = None
        self.refresh()

    def btn_b(self) :
        self.tarevalues = [0.0] * self.tares
        for x in loadcells : x.dotare()

class Calibrate :
    def __init__(self, loadcells):
        self.loadcells = loadcells
        self.name = "Calibrate"

    def init(self):
        splash = displayio.Group()
        display.show(splash)
        self.stage = 0

        self.status_area = label.Label(smallfont, text='Resetting Tare', color=0xFFFFFF, x=20, y=56)
        splash.append(self.status_area)
        for x in self.loadcells : x.begincal()
        #self.refresh()

    def nudge(self):
        if(self.stage == 0):
            self.stage = 1
            self.status_area.text = "Place 500 in pos A"
        if(self.stage == 2):
            self.stage = 3
            self.first = [x.avg - x.tare for x in self.loadcells]
            self.status_area.text = "Place 500 in pos B"
        if(self.stage == 4):
            self.stage = 5
            self.second = [x.avg - x.tare for x in self.loadcells]
            for x in range(0,2) : self.loadcells[x].calibrate([self.first[x], self.second[x]], [self.first[1-x], self.second[1-x]], 500)
            self.status_area.text = "Calibrated"

    def showweight(self, weight, status):
        if status == ads123x.STATUS_OK :
            self.status = status
            self.nudge()
        #self.refresh()

    def btn_a(self) :
        if(self.stage == 1):
            self.stage = 2 
            self.status_area.text = "Waiting"
        if(self.stage == 3):
            self.stage = 4
            self.status_area.text = "Waiting"

    def btn_b(self) :
        pass

class Menu :
    def __init__(self, loadcells):
        self.loadcells = loadcells

    def init(self):
        global mode
        global prevmode
        splash = displayio.Group()
        display.show(splash)

        self.index = 0
        
        self.lines = [label.Label(smallfont, text=x.name, color=0xFFFFFF, x = 8, y = 8 + i * 14) for i,x in enumerate(modes)]
        for x in self.lines : splash.append(x)
        self.update()

    def update(self):
        for i,x in enumerate(self.lines) : 
            if i == self.index : 
                x.color = 0x000000
                x.background_color = 0xFFFFFF
            else :
                x.color = 0xFFFFFF
                x.background_color = 0x000000

    def showweight(self, weight, status):
        pass

    def btn_a(self) :
        self.index = (self.index + 1) % len(modes)
        self.update()

    def btn_b(self) :
        global mode
        global prevmode
        mode = modes[self.index]
        prevmode = self
        mode.init()


def switchmode():
    global mode
    global prevmode
    m = prevmode
    prevmode = mode
    mode = m
    mode.init() 
    #poweroff()

def poweroff():
    adc.powerdown()
    btn_a.deinit()
    btn_b.deinit()
    btn_c.deinit()
    pin_alarm1 = alarm.pin.PinAlarm(pin=board.D5, value=False, pull=True)

    alarm.exit_and_deep_sleep_until_alarms(pin_alarm1) #, pin_alarm2, pin_alarm3)




btn_a = countio.Counter(board.D5)
btn_b = countio.Counter(board.D21)
btn_c = countio.Counter(board.D20)

setdisplay()

adc = ads123x.ADCBoard(board.D18, board.D19, board.D17, board.D16)
adc.powerup()

loadcells = [ads123x.LoadCell(adc, 20.592, False), ads123x.LoadCell(adc, 20.592, True)]

modes = [MultiTare(loadcells), Calibrate(loadcells)]
menu = Menu(loadcells)
mode = modes[0]
mode.init()
prevmode = menu

while True: 
    vals =  [x.pollweight() for x in loadcells]
    wt = sum([x[0] for x in vals])
    status = max([x[1] for x in vals])
    mode.showweight(wt, status)
    if(btn_a.count > 0) :
        mode.btn_a()
        btn_a.reset()
    if(btn_b.count > 0) :
        mode.btn_b()
        btn_b.reset()
    if(btn_c.count > 0) :
        btn_c.reset()
        switchmode()

