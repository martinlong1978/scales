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
        self.tare_area = label.Label(smallfont, text='', color=0xFFFFFF, x=20, y=4)
        self.text_area = label.Label(font, text='', color=0xFFFFFF, x=20, y=30)
        self.status_area = label.Label(smallfont, text='', color=0xFFFFFF, x=20, y=56)
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


    def showweight(self, weight, status):
        self.status = status
        if status == ads123x.STATUS_OK:
            self.weight = round(weight, 1)
        self.refresh()

    def gettarevalue(self) :
        if self.tarecache == None :
            self.tarecache = sum(self.tarevalues) - self.tarevalues[self.active]
        return self.tarecache

    def btn_a(self) :
        self.tarevalues[self.active] = self.weight - self.gettarevalue()
        self.active = (self.active + 1) % 6
        self.tarecache = None
        self.refresh()

    def btn_b(self) :
        self.tarevalues = [0.0] * self.tares
        for x in loadcells : x.dotare()

def switchmode():
    pass

btn_a = countio.Counter(board.D5)
btn_b = countio.Counter(board.D21)
btn_c = countio.Counter(board.D20)

setdisplay()

adc = ads123x.ADCBoard(board.D18, board.D19)
loadcells = [ads123x.LoadCell(adc, 22)]

mode = MultiTare(loadcells)
mode.init()


while True: 
    wt, status = loadcells[0].pollweight()
    mode.showweight(wt, status)
    if(btn_a.count > 0) :
        for i in range(0, btn_a.count):
            mode.btn_a()
        btn_a.reset()
    if(btn_b.count > 0) :
        for i in range(0, btn_b.count):
            mode.btn_b()
        btn_b.reset()
    if(btn_c.count > 0) :
        btn_c.reset()
        switchmode()

