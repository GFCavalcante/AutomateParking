#!/usr/bin/env python

from __future__ import print_function
import qwiic_proximity
import qwiic_oled_display
import time
import datetime
import sys
import mfrc522
import signal
import pigpio
import pyrebase
import RPi.GPIO as GPIO
import threading as th
from time import sleep
from gpiozero import Servo
from qwiic_oled_base import oled_logos as disp_logo

LED_PIN = 23
LED_PIN_RED = 17
LED_PIN_GREEN = 5
SERVO_PIN = 13
ledFrequency = 0.5
continue_reading = True
myOLED = qwiic_oled_display.QwiicOledDisplay()
    
def setUpLed():
    GPIO.setmode(GPIO.BCM)
    
    GPIO.setup(LED_PIN, GPIO.OUT)
    GPIO.output(LED_PIN, GPIO.HIGH)
    
    GPIO.setup(LED_PIN_RED, GPIO.OUT)
    GPIO.output(LED_PIN_RED, GPIO.LOW)    
    
    GPIO.setup(LED_PIN_GREEN, GPIO.OUT)
    GPIO.output(LED_PIN_GREEN, GPIO.HIGH)

def standbyBlink():  
    while True:
        GPIO.output(LED_PIN, GPIO.HIGH)
        time.sleep(ledFrequency)
        GPIO.output(LED_PIN, GPIO.LOW)
        time.sleep(ledFrequency)
    if ledFrequency == 0:
        GPIO.output(LED_PIN, GPIO.HIGH)
        time.sleep(2.75)
                
def nextCarDelay():
    print("\n   Car left range.")
    print("   Closing gate...")
    time.sleep(1)
    print("   3...")
    time.sleep(1)
    print("   2...")
    time.sleep(1)
    print("   1...")
    time.sleep(1)
    print("   Parking Gate Closed!\n\n---Waiting for cars---")

# Capture SIGINT for cleanup when the script is aborted       
def end_read(signal,frame):
    global continue_reading
    print ("Ctrl+C captured, ending read.")
    continue_reading = False
    GPIO.cleanup()
        
def defaultMessage():
    myOLED.begin()
    myOLED.clear(myOLED.PAGE)
    myOLED.clear(myOLED.ALL)  
    myOLED.print("                       AUTOMATED PARKING") 
    myOLED.display()
    
def autoPark():
    global ledFrequency
    gate_open = False
    gate_close = True
    
    # Firebase: User Login Data
    data = {
        "fullname": "Automated Parking",
        "email": "automated.parking@gmail.com",
        "pwd": "autopark"
    }
    # Current Time and Date
    current_time = datetime.datetime.now()
    time_str = current_time.strftime("%d/%m/%Y - %H:%M")
    
    oProx = qwiic_proximity.QwiicProximity()
    
    setUpLed()
#   startUpBlink()
    
    # Firebase Setup
    config = {
        "apiKey": "AIzaSyDcCCJWefS13T4cU05IJFnZtloFJO3yTLY",
        "authDomain": "ezpark-7cf76.firebaseapp.com",
        "databaseURL": "https://ezpark-7cf76-default-rtdb.firebaseio.com",
        "projectId": "ezpark-7cf76",
        "storageBucket": "ezpark-7cf76.appspot.com",
        "messagingSenderId": "103330481504",
        "appId": "1:103330481504:web:22007a21929ea345838a05",
        "measurementId": "G-JYWZVBK079"
    }
    firebase = pyrebase.initialize_app(config)
    auth = firebase.auth()
    db = firebase.database()
    
    # NFC Setup
    signal.signal(signal.SIGINT, end_read)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(27,GPIO.OUT)
    MIFAREReader = mfrc522.MFRC522()
    
    # Servo Setup
    GPIO.setup(SERVO_PIN, GPIO.OUT)
    servo = Servo(SERVO_PIN)
    servo.max()
    
    # Display Setup
    defaultMessage()

    # Proximity Sensor Setup
    oProx.begin()
    oProx.set_led_current(200)
    oProx.set_prox_integration_time(8) # 1 to 8 is valid
    startingProxValue=0 # Take 8 readings and average them
    for x in range(8):
        startingProxValue += oProx.get_proximity()
    startingProxValue /= 8
    deltaNeeded = startingProxValue * 0.05 # Look for %5 change
    if deltaNeeded < 5:
        deltaNeeded = 5   # set a min value
    
    # Threading Led
#     thread = th.Timer(1,standbyBlink)
#     thread.start()

    while continue_reading:

        # Scan for cards
        (status,TagType) = MIFAREReader.MFRC522_Request(MIFAREReader.PICC_REQIDL)

        # If a card is found
        if status == MIFAREReader.MI_OK:
            print ("Card detected")

        # Get the UID of the card
        (status,uid) = MIFAREReader.MFRC522_Anticoll()

        # If we have the UID, continue
        if status == MIFAREReader.MI_OK:

            # Print UID
            print ("Card read UID: "+str(uid[0])+","+str(uid[1])+","+str(uid[2])+","+str(uid[3])+','+str(uid[4]))
            # This is the default key for authentication
            key = [0xFF,0xFF,0xFF,0xFF,0xFF,0xFF]

            # Select the scanned tag
            MIFAREReader.MFRC522_SelectTag(uid)

            #ENTER Your Card UID here
            my_uid = [195,140,167,29,245]
            exit_uid = [83,75,216,27,219]
            #Configure LED Output Pin

            #Check to see if card UID read matches your card UID
            if uid == my_uid:
                myOLED.begin()
                myOLED.clear(myOLED.PAGE)
                myOLED.clear(myOLED.ALL)  # clear the display's memory buffer
                myOLED.print("                            WELCOME")  # print the text
                myOLED.display()
                db.child("Users").child("RSumL5aFj8P7qaxWTIHw3icKJ2Z2").child("History").child("Entry").push(time_str)
                if gate_open == False:
                    servo.mid()
                    gate_open = True
                    gate_close = False
                time.sleep(5)
                 # Begin operation loop
                nothingThere = True
                while True:
                    proxValue = oProx.get_proximity()
                    
                    if proxValue > startingProxValue + deltaNeeded:
                        nothingThere = False
                        print("   Car within range: %d" % proxValue)
                        ledFrequency = 0

                    elif not nothingThere:
                        nextCarDelay()
                        if gate_close == False:
                            servo.max()
                            gate_close = True
                            gate_open = False
                        ledFrequency = 0.5
                        nothingThere=True
                        break
                time.sleep(2)
                defaultMessage()
                uid = 123
            elif uid == exit_uid:
                payment = db.child("Users").child("RSumL5aFj8P7qaxWTIHw3icKJ2Z2").child("Payment").get()
                validation = payment.val()
                myOLED.begin()
                myOLED.clear(myOLED.PAGE)
                myOLED.clear(myOLED.ALL)  # clear the display's memory buffer
               
                if validation == True:
                    myOLED.print("                            GOODBYE")  # print the text
                    myOLED.display()
                    db.child("Users").child("RSumL5aFj8P7qaxWTIHw3icKJ2Z2").child("History").child("Exit").push(time_str)
                    if gate_open == False:
                        servo.mid()
                        gate_open = True
                        gate_close = False
                    # Begin operation loop
                    nothingThere = True
                    while True:
                        proxValue = oProx.get_proximity()
                        
                        if proxValue > startingProxValue + deltaNeeded:
                            nothingThere = False
                            print("   Car within range: %d" % proxValue)
                            ledFrequency = 0

                        elif not nothingThere:
                            nextCarDelay()
                            if gate_close == False:
                                servo.max()
                                gate_close = True
                                gate_open = False
                            ledFrequency = 0.5
                            nothingThere=True
                            break
                    time.sleep(2)
                    defaultMessage()
                    uid = 123

                else:
                    myOLED.print("  PLEASE PAY BEFORE         LEAVING")  # print the text
                    myOLED.display()
                    GPIO.output(LED_PIN_RED, GPIO.HIGH)
                    GPIO.output(LED_PIN_GREEN, GPIO.LOW)               
                    time.sleep(5)
                    defaultMessage()
                    uid = 123
                    GPIO.output(LED_PIN_RED, GPIO.LOW)
                    GPIO.output(LED_PIN_GREEN, GPIO.HIGH)                                       
    time.sleep(.4)
    GPIO.cleanup()
if __name__ == '__main__':
	try:
		autoPark()
	except (KeyboardInterrupt, SystemExit) as exErr:
		print("\nSystem Shutdown")
		sys.exit(0)
  
  