import argparse, sys

#Set Parameters
nozzleoffset = 65
twait = 10
threadD = 0.33

#Function to find return number in string
def get_num(x):
    return float(''.join(ele for ele in x if ele.isdigit() or ele == '.'))

#Set Arguments
parser = argparse.ArgumentParser()
parser.add_argument("file", help="Name of file to modify")
parser.add_argument("-w", "--wrapheight", help="Height of Wrapped Section", type = float)
parser.add_argument("-o", "--offset", help="Offset we want to wrap from", type = float, )
parser.add_argument("-l", "--loops", help="Number of loops (up and down = 2 loops", type =int)
parser.add_argument("-n", "--name", help="Name of Output File")
parser.add_argument("-s", "--silent", help="Silent Mode - Suppress Output to Screen", action="store_true")
args = parser.parse_args()

#Set Defaults
if args.loops == None:
	args.loops = 1

if args.offset == None:
	args.offset = 0

if args.wrapheight == None:
	args.wrapheight = 130

if args.name == None:
	args.name = "Loop_{}x{}".format(args.loops,args.file)

#Output Options Selected to Screen
if not args.silent:
	print("Looping \"{}\" {} times".format(args.file, args.loops))
	print("Offset: {}mm, Wrap Height: {}mm".format(args.offset,args.wrapheight))

#Error Check
if args.wrapheight > 130:
	sys.exit("ERROR - Exceeding Max Wrap Height of 130mm")

if args.wrapheight +args.offset +nozzleoffset > 205:
	sys.exit("ERROR - Exceeding Max Height of 205mm")

#Open Files
finput = open(args.file, 'r')
data = finput.readlines()
finput.close()
if not args.silent:
	print("Opening \"{}\" for output".format(args.name))
foutput = open(args.name, 'w')	#write file to output

#Initialise Values
line = 0
endl = -1

#Read in Gcode File Details, Recalc for output, del lines from loop array
while "G0" not in data[line]: #skip start of gcode
	if "TIME" in data[line]:
		ftime = get_num(data[line])
		
	if "LAYER_COUNT" in data[line]:
		fheight = get_num(data[line])*threadD #No. Layers * Layer Height
		
		if args.wrapheight > fheight:
			args.wrapheight = fheight
			print("ERROR - File WrapHeight = {:.2f}".format(fheight))

		time = (ftime / fheight)*args.wrapheight*args.loops #find s/Zmm
	del data[line]

#Print Time to Screen
if not args.silent:
	print("Total TIME: {:.0f}s or {:.0f}mins or {:.2f}hrs".format(time,time/60,time/3600))

#Write Setup Values to file
foutput.write(";SETUP\n")
foutput.write(";TIME:{:.0f}s or {:.0f}mins or {:.2f}hrs\n".format(time,time/60,time/3600))
foutput.write(";Offset {:.2f}mm, Wrap Height: {:.2f}mm, Loops: {}\n".format(args.offset, args.wrapheight, args.loops))
foutput.write(";Generated with Cura, edited w/ JC Gcode Art\n")
foutput.write("\n")
foutput.write("G28 ;Home all Axes\n")
foutput.write("M107 ;Set Fan to Off\n")
foutput.write("M140 S-273.15 ;Set Bed Temp to Off\n")
foutput.write("M104 S20 ;Set Hot End to 20deg C\n")
foutput.write("M302 S0 ;Allow Cold Extrusion\n")
foutput.write("\n")

#Initilise Printer
foutput.write("G0 F6000 X0 Y0 ;Go to Starting Corner\n")
foutput.write("G4 S{0} ;Wait {0} seconds\n\n".format(twait)) #and wait x seconds here


#Modify GCode - remove Extrude and Fan commands, offset Z, find loop endpoint
startl = line	#note start of print 
for line in range(len(data)):
	if data[line][0] == "G":
		segment = data[line].split(" ")
		for i, piece in enumerate(segment):
			if "E" in piece:
				segment[i] = "\n"
			if "Z" in piece:
				zheight = get_num(piece)
				segment[i] = "Z{:.2f} ".format(zheight+args.offset+nozzleoffset)
				if  zheight > args.wrapheight:
					endl = line
					break
		else:
			data[line] = " ".join(segment) #build line
			continue
		data[line] = ""
		break
	if data[line][0] == ";" and "LAYER" not in data[line]:
		data[line] = "" #delete Non Layer Comments
	if "M106" in data[line] or "TIME_ELAPSED" in data[line]:
		data[line] = ""

	if data[line] == "G10\n":	#end found, exit
		break

#Remove end of Gcode
for line in range(line,len(data)):
	data[line] = ""

#Error Check endl Value
if endl == -1:
	endl = len(data)

#Write Loop to Output
for loop in range(0,args.loops):

	if loop % 2 == 0:

		foutput.write(";---- Loop No: {} ----\n".format(loop))
		foutput.write(";LAYER:0\n")

		for line in range(len(data)):
			foutput.write("%s" %data[line])
		
		foutput.write("G0 F6000 X0 Y0 ;Go to Starting Corner\n")
		foutput.write("G4 S{0} ;Wait {0} seconds\n".format(twait)) #and wait x seconds here

	else: 
		foutput.write("\n;-----REVERSE-----\n\n")
		foutput.write(";---- Loop No: {} ----\n".format(loop))

		for line in range(endl-1, startl-1, -1): 	#len(data)-4 so we don't copy the Move and Wait
			foutput.write("%s" %data[line])
		foutput.write("G0 F6000 Z200 ;Move Away From Part\n")
		foutput.write("G4 S{0} ;Wait {0} seconds\n".format(twait)) #and wait x seconds here

#Write final lines to Output and close
foutput.write("{} Loops complete\n".format(args.loops))
foutput.write("M84 ;disable motors".format(args.loops))
foutput.close()