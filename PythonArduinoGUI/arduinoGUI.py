from tkinter import *
from arduinoComms import *
import atexit

def exit_handler():
    print('My application is ending!')
    closeSerial()

atexit.register(exit_handler)

# global variables for this module
ledAstatus = 0
ledBstatus = 0
servoPos = 10


tkArd = Tk()
tkArd.minsize(width=320, height=170)
tkArd.config(bg = 'yellow')
tkArd.title("Arduino GUI Demo")

def setupView():
	global masterframe
	masterframe = Frame(bg = "yellow")
	masterframe.pack()
	
	selectPort()

def runProgram():
	tkArd.mainloop()	

def selectPort():
	global masterframe, radioVar
	for child in masterframe.winfo_children():
		child.destroy()
	radioVar = StringVar()

	lst = listSerialPorts()
	
	l1= Label(masterframe, width = 5, height = 2, bg = "yellow") 
	l1.pack()

	if len(lst) > 0:
		for n in lst:
			r1 = Radiobutton(masterframe, text=n, variable=radioVar, value=n, bg = "yellow")
			r1.config(command = radioPress)
			r1.pack(anchor=W)
	else:
		l2 = Label(masterframe, text = "No Serial Port Found")
		l2.pack()

	
def mainScreen():
	global masterframe
	for child in masterframe.winfo_children():
		child.destroy()
		
	labelA = Label(masterframe, width = 5, height = 2, bg = "yellow") 
	labelB = Label(masterframe, width = 5, bg = "yellow") 
	labelC = Label(masterframe, width = 5, bg = "yellow") 
	
	ledAbutton = Button(masterframe, text="LedA", fg="white", bg="black")
	ledAbutton.config(command = lambda: btnA(ledAbutton))
	
	ledBbutton = Button(masterframe, text="LedB", fg="white", bg="black")
	ledBbutton.config(command = lambda:  btnB(ledBbutton))
	
	slider = Scale(masterframe, from_=10, to=170, orient=HORIZONTAL)
	slider.config(command = slide)
	
	labelA.grid(row = 0)
	ledAbutton.grid(row = 1)
	labelB.grid(row = 1, column = 2)
	ledBbutton.grid(row = 1, column = 3)
	labelC.grid(row = 2)
	slider.grid(row = 3, columnspan = 4)
	
	
def btnA(btn):
	global ledAstatus, ledBstatus, servoPos
	
	if ledAstatus == 0:
		ledAstatus = 1
		btn.config(bg="white", fg="black")
	else:
		ledAstatus = 0
		btn.config(fg="white", bg="black")
	valToArduino(ledAstatus, ledBstatus, servoPos)

def btnB(btn):
	global ledAstatus, ledBstatus, servoPos
	
	if ledBstatus == 0:
		ledBstatus = 1
		btn.config(bg="white", fg="black")
	else:
		ledBstatus = 0
		btn.config(fg="white", bg="black")
	valToArduino(ledAstatus, ledBstatus, servoPos)


def slide(sval):
	global ledAstatus, ledBstatus, servoPos
	
	servoPos = sval
	valToArduino(ledAstatus, ledBstatus, servoPos)

def radioPress():
	global radioVar
	setupSerial(radioVar.get())
	mainScreen()

setupView()
tkArd.mainloop()	
