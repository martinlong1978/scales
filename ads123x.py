import digitalio
import time

buffersize = 10

STATUS_WAITING = 0
STATUS_OK = 0
STATUS_SETTLE = 1
STATUS_TARE = 2

# this should allow handing of ADS1232 and ADS1234 boards. 

class ADCBoard :

    def __init__(self, clockpin, datapin, powerpin, inputselect):
        self.clk = digitalio.DigitalInOut(clockpin)
        self.da = digitalio.DigitalInOut(datapin)
        self.pwr = digitalio.DigitalInOut(powerpin)
        self.islc = digitalio.DigitalInOut(inputselect)

        self.clk.direction = digitalio.Direction.OUTPUT
        self.pwr.direction = digitalio.Direction.OUTPUT
        self.islc.direction = digitalio.Direction.OUTPUT

    def readbit(self):
        self.clk.value = True
        self.clk.value = False
        time.sleep(0.0000002)
        v = self.da.value
        return v

    def readvalue(self, input):
        self.islc.value = input
        self.clk.value = False
#        time.sleep(0.0000002)
        test = 0
        while(test < 15):
            test = (test + 1) if self.da.value == False else 0
            time.sleep(0.002)
        val = 0
        for x in range(0,24):
            val = val * 2
            v = self.readbit() 
            if x == 0 : posneg = v # handle 2's compliment negative numbers
            val += (-1 if not v else 0) if posneg else (1 if v  else 0) 
        # 25th pulse
        self.readbit()
        self.clk.value = False
        return val
    
    def powerdown(self):
        self.pwr.value = False

    def powerup(self):
        self.pwr.value = True
        self.pwr.value = False
        self.pwr.value = True

class LoadCell :

    def __init__(self, board, calibration, input):
        self.ringbuffer = [0] * buffersize
        self.tmpringbuffer = [0] * buffersize
        self.pointer = 0
        self.tmppointer = 0
        self.cal = calibration
        self.avg = 0
        self.board = board
        self.tare = 0
        self.input = input


    def pollweight(self):
        val = 16777215
        while val == 16777215 :
            val = self.board.readvalue(self.input)
        if self.cal > 1 and abs(self.avg - val)  > (self.cal * 3) :
            self.tmpringbuffer[self.tmppointer] = val
            self.tmppointer += 1 
            if(self.tmppointer >= buffersize):
                t = self.ringbuffer
                self.ringbuffer = self.tmpringbuffer
                self.pointer = buffersize
                self.tmppointer = 0
                self.tmpringbuffer = t
            else :
                return 0, STATUS_TARE if self.tare == 0 else STATUS_SETTLE 
        else:
            self.ringbuffer[self.pointer] = val
            self.pointer += 1 
            self.tmppointer = 0
        self.avg = round(sum(self.ringbuffer) / buffersize)
        if(self.pointer >= buffersize):
            self.pointer = 0
            if self.tare == 0 :
                self.tare = self.avg
        if(self.tare == 0):
            return 0, STATUS_TARE
        return (self.avg - self.tare) / self.cal, STATUS_OK

    def dotare(self):
        self.tare = 0

    def begincal(self):
        self.dotare()
        self.cal = 1
    
    def calibrate(self, calreadings, refreadings, target):
        print(f"{calreadings}, {refreadings}")
        ratio = (calreadings[0] - calreadings[1])/(refreadings[1] - refreadings[0])
        sum = calreadings[0] + (refreadings[0] * ratio)
        self.cal = sum / target
        print(f"Calibration set to {self.cal}")

