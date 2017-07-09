import argparse

def get_num(x):
    return float(''.join(ele for ele in x if ele.isdigit() or ele == '.'))

parser = argparse.ArgumentParser()
parser.add_argument("-w", "--wrapheight", type = float, help="Height of Wrapped Section")
parser.add_argument("-o", "--offset", type = float, help="Offset we want to wrap from")
parser.add_argument("-f", "--file", help="Name of file to convert")
parser.add_argument("-l", "--loops", type =int, help="Number of loops(up and down = 2 loopsstop at top)")
args = parser.parse_args()

if args.loops == None:
	args.loops = 1

if args.offset == None:
	args.offset = 0

if args.wrapheight == None or args.wrapheight > 130:
	args.wrapheight = 130

print("Offset: {}, Wrap Height: {}".format(args.offset,args.wrapheight))

nozzleoffset = 0
twait = 10

args.offset += nozzleoffset

print("Looping {} {} times".format(args.file, args.loops))

finput = open(args.file, 'r')
data = finput.readlines()
finput.close()

foutput = open("loop_".format(args.loops)+args.file, 'w')	#write file to output
foutput.write(";SETUP\n")

line = 0
endl = -1

while "G0" not in data[line]: #skip start of gcode
	if "TIME" in data[line]:
		time = 2 * get_num(data[line]) * args.loops #extract time and multiply by number of loops
		print("Total TIME: {:.0f}s or {:.0f}mins or {:.2f}hrs".format(time,time/60,time/3600))
		foutput.write(";TIME:{:.0f}s or {:.0f}mins or {:.2f}hrs\n".format(time,time/60,time/3600))
	if "LAYER_COUNT" in data[line]:
		foutput.write("%s" %data[line])
	del data[line]

foutput.write("G28 ;Home all Axes\n")
foutput.write("M107 ;Set Fan to Off\n")
foutput.write("M140 S-273.15 ;Set Bed Temp to Off\n")
foutput.write("M104 S20 ;Set Hot End to 20deg C\n")
foutput.write("M302 S0 ;Allow Cold Extrusion\n")
foutput.write(";Generated with Cura 2.5.0, edited w/ JC Gcode Art\n")
foutput.write("\n")

data.insert(line,"G4 S{0} ;Wait {0} seconds\n".format(twait)) ; line+=1 # wait x seconds here 
data.insert(line, "G0 F6000 X0 Y{} ;Go to Starting Corner\n".format(args.offset)); line+=1

startl = line	#note start of print as Starting Corner
for line in range(len(data)):	#remove extrude & fan commands
	if data[line][0] == "G":
		segment = data[line].split(" ")
		for i, piece in enumerate(segment):
			if "E" in piece:
				segment[i] = "\n"
			if "Z" in piece:
				zheight = get_num(piece)
				segment[i] = "Z{:.2f} ".format(zheight+args.offset)
				print(piece)
				if  zheight > args.wrapheight:
					endl = line
					print("end line:{}".format(line))
					break
		else:
			data[line] = " ".join(segment)
			continue
		data[line] = ""
		break
	if "M106" in data[line] or "TIME_ELAPSED" in data[line]:
		data[line] = ""

	if data[line] == "G10\n":	#end found, exit
		break

#print("start, Line:{}, {}".format(startl,data[startl]),end ="")

while "End" not in data[line]:	#skip to end of Gcode
	del data[line]

endlines = list()	#save end of Gcode
while line < len(data):
	endlines.append(data[line])
	del data[line]

if endl == -1:
	endl = len(data)

data.insert(endl,"G4 S{0} ;Wait {0} seconds\n".format(twait)) #and wait x seconds here
data.insert(endl,";MOVE AWAY\n")	#Move away from part

#data.append("M117 P\"ARTISTIC MESSAGE and press OK when done\" S2") #resumes when user presses enter
#data.append("M0")

data.append("\n;-----REVERSE-----\n\n")

for line in range(endl-1, startl-1, -1): 	#len(data)-4 so we don't copy the Move and Wait
	data.append(data[line])						#startl-1 so we include the starting movement

data.append("G0 F6000 X0 Y0 ;Go to Starting Corner\n"); line+=1
data.append("G4 S{0} ;Wait {0} seconds\n".format(twait)) #and wait x seconds here

for loop in range(0,args.loops):
	if loop % 2 == 0:
		foutput.write("---- Loop No: {} ----\n".format(loop))
		foutput.write(";LAYER:0\n")
	else: 
		for line in range(len(data)):
			foutput.write("%s" %data[line])

foutput.write("{} Loops complete\n".format(args.loops))
foutput.write("M84 ;disable motors".format(args.loops))

foutput.close()