from common.diagrams import Diagram

from residue.models import Residue
from residue.models import ResidueGenericNumber
from residue.models import ResidueNumberingScheme

from django.utils.safestring import mark_safe

from math import cos, sin, pi, floor,sqrt
from datetime import datetime


class DrawSnakePlot(Diagram):

    def __init__(self, residue_list, protein_class,protein_name, nobuttons = None):
        self.nobuttons = nobuttons
        self.type = 'snakeplot'
        plot_data = {}
        plot_data['direction'] = [0,0, 1, 0, 1, 0, 1, 0]; # 0: EC->IC, 1: IC->EC
        plot_data['helixRadius'] = 70;
        # Class A
        plot_data['Class A'] = {}
        plot_data['Class A']['coordinates'] = [0,[455,240],[385,108],[245,118],[105,95],[75,235],[185,320],[324,303]]
        plot_data['Class A']['helixTopResidues'] = [0,'1x32', '2x63', '3x26', '4x61', '5x39', '6x57', '7x32']
        plot_data['Class A']['helixTopResidues'] = [0,32, 63, 26, 61, 39, 57, 32]
        plot_data['Class A']['rotation'] = [0,340, 320, 290, 125, 40, 180, 130] # in degrees

        # Class C
        plot_data['Class C'] = {}
        plot_data['Class C']['coordinates'] = [0, [455,231],[390,108],[245,118],[105,105],[75,241],[193,320],[328,303]]
        plot_data['Class C']['helixTopResidues'] = [0, 34, 61, 26, 61, 38, 57, 35]

        self.receptorId = protein_name
        self.family = protein_class
        self.output = ''
        residueType = 'sp'

        #FIXME DO PUREIMAGE
        pureImage = False
        #$pureImage = isset($_GET['pureimage']) && $_GET['pureimage'] == 'TRUE' ? TRUE : FALSE;
        
        # get sequence, baldwin, and bw information of this receptor

        self.sequence = residue_list


        #self.residuelist = Residue.objects.values_list('generic_number', flat=True).filter(protein_conformation__protein__entry_name=self.receptorId)
        #self.segments = Residue.objects.filter(protein_conformation__protein__entry_name=self.receptorId).order_by().values_list('protein_segment__slug', flat=True).distinct()


        #self.segments = dict.fromkeys(self.segments, [])
        self.segments = {}
        #print("residues",len(self.sequence))
        i = 0
        for r in self.sequence:
            if r.protein_segment:
                segment = str(r.protein_segment.slug)
            elif r.segment_slug: #from family aligment
                segment = str(r.segment_slug)

            if segment not in self.segments: self.segments[segment] = []
            label = ''
            displaylabel = ''
            if r.generic_number: 
                label = r.generic_number.label
            elif hasattr(r, 'family_generic_number'):
                label = r.family_generic_number
            if r.display_generic_number: displaylabel = r.display_generic_number.label
            displaylabel = r.amino_acid + str(r.sequence_number) + " \n " + displaylabel
            if hasattr(r, 'extra'):
                displaylabel = displaylabel + "\n" + r.extra
            self.segments[segment].append([r.sequence_number,r.amino_acid,label,displaylabel])
            #print(segment,len(self.segments[segment]))
            #print(r.sequence_number,r.amino_acid,r.protein_segment.slug)
            i += 1
        #print(i)

        #print(self.segments)
        #for segment in self.segments:
            #print(segment,len(self.segments[segment]))
        
        #$baldwin =  Receptor::GetReceptorProperty($receptorId, 'baldwin');
        #$baldwin = explode(";", $baldwin);

        self.helixWidth = 85           # Width of helix
        self.resNumPerRow = 4          # Residue number per row in helix
        self.angleDeg = 22.0           # Angle size of each helix turn
        self.residue_radius = 12     # Radius of the residue circle

        # svg image padding offset
        self.offsetX = 20
        self.offsetY = 50

        # margin between two helixes
        self.margin = 30
        
        #highest and lowest bound of this svg
        self.high =100
        self.low = 0

        #keep track of max Y positions of intra/extra loops
        self.maxY = {'intra':0,'extra':0}
        self.maxX = {'left':0,'right':0}

        # helices length
        #helicesLength = Svg::getSnakePlotHelicesLength($baldwin, $helixWidth, $angleDeg) #FIXME
        
        # top and bottom residue coords in each helix
        self.TBCoords = {}

        
        self.output = ""
        self.traceoutput = ""
        self.helixoutput = ""


        for i in range(1,8):
            try:
                self.helixoutput += self.drawSnakePlotHelix(i)
            except Exception as msg:
                self.TBCoords[i] = {}
                startX = self.helixWidth+self.offsetX+(self.margin+self.helixWidth)*(i-1)
                startY = self.offsetY
                self.TBCoords[i]['extra'] = [startX,startY]
                self.TBCoords[i]['intra'] = [startX,startY+140]
                print('error with helix',i,msg)
                pass

        if "H8" in self.segments: #if helix8
            self.helixoutput += self.drawSnakePlotHelix8()
        
        #print(self.TBCoords)

        self.drawSnakePlotLoops()
        self.drawSnakePlotTerminals()

        #print(self.maxY)
        #print(self.maxX)
        #self.output +=self.drawToolTip()



    def __str__(self):  

        self.output = "<g id=snake transform='translate(0, " + str(-self.low+ self.offsetY) + ")'>" + self.traceoutput+self.output+self.helixoutput+self.drawToolTip() + "</g>"; #for resizing height
        return mark_safe(self.create(self.output,self.maxX['right']+30,self.high-self.low+self.offsetY*2,"snakeplot", self.nobuttons))

    def drawSnakePlotHelix(self, helix_num):
        #print('drawing helix nr',helix_num)
        rs = self.segments['TM'+str(helix_num)]
        #print(residues)
        #print(len(self.segments['TM'+str(helix_num)]), "residues")
        self.TBCoords[helix_num] = {}

        if helix_num%2==0: rs.reverse() #reverse direction for even helix because they go from inside to outside
        

        res_num = len(self.segments['TM'+str(helix_num)])
        output_residue_in = ''
        output_residue_out = ''
        output_trace = ''

        startX = self.helixWidth+self.offsetX+(self.margin+self.helixWidth)*(helix_num-1)
        startY = self.offsetY

        row_length = 3
        row_pos = 0
        row = 0
        prevGeneric = '0x0'
        bulgeX = 0
        bulgeY = 0
        bulge = 0
        skip = 0
        indentX = -self.residue_radius+3
        indentY = 3 
        for i in range(0,res_num):
            #print(rs[i])
            #print(rs[i][2].split('x'))
            prevGeneric_number = prevGeneric.split('x')[1]
            currGeneric_number = rs[i][2].split('x')[1]
            if (helix_num%2!=0 and prevGeneric_number+'1'==currGeneric_number) or (helix_num%2==0 and str(int(prevGeneric_number)-1)+'1'==currGeneric_number):
                #print('BULGE!',rs[i])
                bulge = 1
                if row_pos==0:  #if first in row, use space for bulge
                    bulgeY = 5
                    bulgeX = 7
                else: 
                    bulgeY = 5
                    bulgeX = 5
                row_length+=1
            elif i!=0 and ((helix_num%2==0 and int(prevGeneric_number)-1!= int(currGeneric_number)) or (helix_num%2!=0 and int(prevGeneric_number)+1!= int(currGeneric_number))):
                #print(i,'something missing?')
                skip = 1
                if row_pos!=0 and row_pos+1<row_length: 
                    nextX =round(startX-(row_pos+1)*self.residue_radius*1.5+indentX+bulgeX)
                    nextY = round(startY+row*self.residue_radius*2.4+(row_pos+1)*self.residue_radius*0.5+indentY+bulgeY)
                    output_trace += "<line x1="+str(prevX)+" y1="+str(prevY)+" x2="+str(nextX)+" y2="+str(nextY)+" stroke='grey' fill='none' stroke-width='1' stroke-dasharray='1,1' />"
                    row_pos +=1
                elif row_pos+1==row_length:
                    row+=1
                    row_pos=0
                    row_length = 3 if row_length == 4 else 4
                else:
                    row_pos +=1
            
            #else:
                #bulgeY = 0
            x = round(startX-row_pos*self.residue_radius*1.6+indentX+bulgeX) #move left as you go down a row
            y = round(startY+row*self.residue_radius*2.4+row_pos*self.residue_radius*0.5+indentY+bulgeY) #Move down with right amount
            output_residue = self.DrawResidue(x,y,rs[i][1], rs[i][0], rs[i][3], self.residue_radius)


            if x<self.maxX['left']: self.maxX['left'] = x
            if x>self.maxX['right']: self.maxX['right'] = x

            row_pos += 1
            if bulge==1:
                if row_pos==1:  #if first in row, use space for bulge
                    bulgeY = -3
                    bulgeX = 10
                else: 
                    bulgeY = -3
                    bulgeX = 7
                rs[i][2] = prevGeneric #make it the prev one, to catch missing ones correctly
                bulge = 0

            if row_length==3: 
                output_residue_in += output_residue
            else:
                output_residue_out += output_residue


            if i==0: self.TBCoords[helix_num]['extra'] = [x,y]
            if i==res_num-1: self.TBCoords[helix_num]['intra'] = [x,y]


            if (row_pos==1 and row!=0) or (skip==1 and row_pos==2): #if need for trace
                #print('trace!')
                if row_length==3: points = "M "+str(prevX)+" "+str(prevY)+" Q"+str(prevX-40)+" "+str(prevY+30)+", "+str(x-21)+" "+str(y-8)+" T"+str(x)+" "+str(y)
                if row_length>=4: points = "M "+str(prevX)+" "+str(prevY)+" Q"+str(prevX-40)+" "+str(prevY+30)+", "+str(x-24)+" "+str(y-7)+" T"+str(x)+" "+str(y)
                #points = "M "+str(prevX)+","+str(prevY)+" C"+str(prevX-50)+","+str(prevY+20)+" "+str(x-25)+","+str(y+20)+" "+str(x+10)+","+str(y)
                output_trace += "<path d='" + points + "' stroke='grey' fill='none' stroke-width='1' stroke-dasharray='1,2' />"

            #alternate between 4 and 3 res per row
            if row_length>3 and row_pos>=row_length: 
                row_length=3
                row_pos = 0
                row += 1
                bulgeX = 0
                bulgeY = 0
                indentX = -self.residue_radius+3
                indentY = 3 
            elif row_length==3 and row_pos>=3:
                row_length=4
                row_pos = 0
                row += 1
                bulgeX = 0
                bulgeY = 0
                indentX = 0
                indentY = 0


            skip = 0
            prevX = x
            prevY = y
            prevGeneric = rs[i][2]

        return output_trace+output_residue_in+output_residue_out

    def drawSnakePlotHelix8(self):
        #print('drawing helix nr8')
        helix_num = 8
        rs = self.segments['H8']
        #print(residues)
        #print(len(self.segments['TM'+str(helix_num)]), "residues")
        self.TBCoords[helix_num] = {}

        #if helix_num%2==0: rs.reverse() #reverse direction for even helix because they go from inside to outside
        

        #print(rs)
        # rs = []
        # for r in temprs:
        #     if len(r[2])>2:
        #         rs.append(r)
        # print(rs)
        res_num = len(rs)
        output_residue_in = ''
        output_residue_out = ''
        output_trace = ''

        startX = self.TBCoords[7]['intra'][0]+40
        startY =  self.TBCoords[7]['intra'][1]+40

        row_length = 3
        row_pos = 0
        row = 0
        prevGeneric = '0x0'
        bulgeX = 0
        bulgeY = 0
        bulge = 0
        skip = 0
        indentX = -self.residue_radius+3
        indentY = 3 
        for i in range(0,res_num):
            #print(rs[i])
            #if rs[i][2]=='': continue #skip if no generic number FIXME
            #print(rs[i][2].split('x'))
            if rs[i][2]!='' and prevGeneric!='':
                prevGeneric_number = prevGeneric.split('x')[1]
                currGeneric_number = rs[i][2].split('x')[1]
                if (helix_num%2==0 and prevGeneric_number+'1'==currGeneric_number) or (helix_num%2!=0 and str(int(prevGeneric_number)-1)+'1'==currGeneric_number):
                    #print('BULGE!',rs[i])
                    bulge = 1
                    if row_pos==0:  #if first in row, use space for bulge
                        bulgeY = 5
                        bulgeX = 7
                    else: 
                        bulgeY = 5
                        bulgeX = 5
                    row_length+=1
                elif i!=0 and ((helix_num%2!=0 and int(prevGeneric_number)-1!= int(currGeneric_number)) or (helix_num%2==0 and int(prevGeneric_number)+1!= int(currGeneric_number))):
                    #print(i,'something missing?')
                    skip = 1
                    if row_pos!=0 and row_pos+1<row_length: 
                        nextX =round(startX-(row_pos+1)*self.residue_radius*1.5+indentX+bulgeX)
                        nextY = round(startY+row*self.residue_radius*2.4+(row_pos+1)*self.residue_radius*0.5+indentY+bulgeY)
                        output_trace += "<line x1="+str(prevX)+" y1="+str(prevY)+" x2="+str(nextX)+" y2="+str(nextY)+" stroke='grey' fill='none' stroke-width='1' stroke-dasharray='1,1' />"
                        row_pos +=1
                    elif row_pos+1==row_length:
                        row+=1
                        row_pos=0
                        row_length = 3 if row_length == 4 else 4
                    else:
                        row_pos +=1
            
            #else:
                #bulgeY = 0
            x = round(startX-row_pos*self.residue_radius*1.6+indentX+bulgeX) #move left as you go down a row
            y = round(startY+row*self.residue_radius*2.4+row_pos*self.residue_radius*0.5+indentY+bulgeY) #Move down with right amount
            x = round(startX+row*self.residue_radius*2.4-row_pos*self.residue_radius*0.5+indentY+bulgeY) #move left as you go down a row
            y = round(startY+row_pos*self.residue_radius*1.6+indentX+bulgeX) #Move down with right amount
            output_residue = self.DrawResidue(x,y,rs[i][1], rs[i][0], rs[i][3], self.residue_radius)


            if x<self.maxX['left']: self.maxX['left'] = x
            if x>self.maxX['right']: self.maxX['right'] = x

            row_pos += 1
            if bulge==1:
                if row_pos==1:  #if first in row, use space for bulge
                    bulgeY = -3
                    bulgeX = 10
                else: 
                    bulgeY = -3
                    bulgeX = 7
                rs[i][2] = prevGeneric #make it the prev one, to catch missing ones correctly
                bulge = 0

            if row_length==3: 
                output_residue_in += output_residue
            else:
                output_residue_out += output_residue


            if i==0: self.TBCoords[helix_num]['extra'] = [x,y]
            if i==res_num-1: self.TBCoords[helix_num]['intra'] = [x,y]


            if (row_pos==1 and row!=0) or (skip==1 and row_pos==2): #if need for trace
                #print('trace!')
                if row_length==3: points = "M "+str(prevX)+" "+str(prevY)+" Q"+str(prevX+10)+" "+str(prevY+50)+", "+str(x-20)+" "+str(y+20)+" T"+str(x)+" "+str(y)
                if row_length==4: points = "M "+str(prevX)+" "+str(prevY)+" Q"+str(prevX+10)+" "+str(prevY+50)+", "+str(x-20)+" "+str(y+20)+" T"+str(x)+" "+str(y)
                #points = "M "+str(prevX)+","+str(prevY)+" C"+str(prevX-50)+","+str(prevY+20)+" "+str(x-25)+","+str(y+20)+" "+str(x+10)+","+str(y)
                output_trace += "<path d='" + points + "' stroke='grey' fill='none' stroke-width='1' stroke-dasharray='1,2' />"

            #alternate between 4 and 3 res per row
            if row_length>3 and row_pos>=row_length: 
                row_length=3
                row_pos = 0
                row += 1
                bulgeX = 0
                bulgeY = 0
                indentX = -self.residue_radius+3
                indentY = 3 
            elif row_length==3 and row_pos>=3:
                row_length=4
                row_pos = 0
                row += 1
                bulgeX = 0
                bulgeY = 0
                indentX = -16
                indentY = 5


            skip = 0
            prevX = x
            prevY = y
            prevGeneric = rs[i][2]

            if i==0:
                points = "M "+str(self.TBCoords[7]['intra'][0])+" "+str(self.TBCoords[7]['intra'][1])+" Q"+str(self.TBCoords[7]['intra'][0]-30)+" "+str(y)+" "+str(x)+" "+str(y)
                self.output += "<path d='" + points + "' stroke='black' fill='none' stroke-width='2' />"

        return output_trace+output_residue_in+output_residue_out

        #return output_trace

    def drawSnakePlotTerminals(self):

        y_offset = 50
        font_size = 12
        font_family = 'courier'
        bezier_pull = 80

        between_residues = 18

        for i in ['N','C']:

            name = i+"-term"
            if name not in self.segments: break #break if no terminus

            rs = self.segments[name] #get residues

            if i=='N':
                orientation = -1
                y_max = self.maxY['extra']-between_residues*4
                x_max = self.maxX['right']
                position = 'extra'
                linked_helix = 1
                rs.reverse()
            else:
                orientation = 1
                y_max = self.maxY['intra']+between_residues*4
                x_max = self.maxX['left']
                position = 'intra'
                linked_helix = 7
                if 8 in self.TBCoords:
                    linked_helix = 8


            x1 = self.TBCoords[linked_helix][position][0]
            y1 = self.TBCoords[linked_helix][position][1]
            #print('Loop',i,position,number)

            #Get positions of two  linking residues from each helix
            x2 = x1-30
            y2 = y1+60*orientation

            #print([x1,y1],[x2,y2])

            #Make line and box for short version
            points = "M "+str(x1)+" "+str(y1)+" Q"+str(x1+30)+" "+str(y2)+" "+str(x2)+" "+str(y2)
            self.output += "<path class='"+name+" short' d='" + points + "' stroke='black' fill='none' stroke-width='2' />"
            self.output += "<rect class='"+name+" short' onclick='toggleLoop(\"."+name+"\",\"short\");' x="+str(x2-25)+" y="+str(y2-13)+" rx=5 ry=5 width='50' height='20' stroke='black' fill='white' stroke-width='1' style2='fill:red;stroke:black;stroke-width:5;opacity:0.5'/>"
            self.output += str("<text class='"+name+" short' onclick='toggleLoop(\"."+name+"\",\"short\");' x="+str(x2)+" y="+str(y2)+" text-anchor='middle' font-size="+str(font_size)+" font-family='"+font_family+"'>"+name+"</text>")


            x2 = x1-90*orientation
            y2 = y_max
            bezierX = x1+60*orientation
            bezierY = (y_max+y1)/2+60*orientation

            points = "M "+str(x1)+" "+str(y1)+" Q"+str(bezierX)+" "+str(bezierY)+" "+str(x2)+" "+str(y2)
            #self.output += "<path d='" + points + "' stroke='black' fill='none' stroke-width='2' class='"+name+" long' />"

            

            pos = 40

            length = self.lengthbezier([x1,y1],[bezierX,bezierY],[x2,y2],0.001)

            bend = 0
            distance_between_rows = 30
            pos_bend = 0
            bend_direction = -1*orientation

            for i in range(0,len(rs)):

                r = rs[i]
                if pos<length:
                    where = self.wherebezier([x1,y1],[bezierX,bezierY],[x2,y2],0.001,pos)
                else:
                    if pos_bend==0 and bend!=0: #if first residue in line put in middle
                        where[1][0] = where[1][0]-between_residues*bend_direction
                        #where[1][0] = where[1][0]
                        where[1][1] = where[1][1]+orientation*distance_between_rows/2
                    elif pos_bend==between_residues and bend!=0: #if 2nd residue in line put in middle
                         #where[1][0] = where[1][0]-between_residues*bend_direction
                         where[1][0] = where[1][0]+between_residues*bend_direction
                         where[1][1] = where[1][1]+orientation*distance_between_rows/2
                    else:
                        where[1][0] = where[1][0]+between_residues*bend_direction
                        where[1][1] =  where[1][1]
                    last_bend_x = where[1][0]
                    last_bend_y = where[1][1]

                    pos_bend += between_residues
                    #print("check",pos_bend,abs(x2-x_max))
                    if pos_bend>=abs(x2-x_max)-40: #no more bend left
                        pos_bend = 0
                        bend += 1
                        if bend_direction==1: 
                            bend_direction = -1
                        elif bend_direction==-1: 
                            bend_direction = 1

                    #where = self.wherebezier([x1,y1],[bezierX,bezierY],[bezierX2,bezierY2],0.001,pos,[x2,y2])

                if i==0: self.output += "<line class='"+name+" long' x1="+str(x1)+" y1="+str(y1)+" x2="+str(where[1][0])+" y2="+str(where[1][1])+" stroke='black' fill='none' stroke-width='2' stroke-dasharray2='1,1' />"

                if bend==0: labely = where[1][1]

                self.output += self.DrawResidue(where[1][0],where[1][1],r[1], r[0], rs[i][3], self.residue_radius-1,name+" long")
                pos += between_residues

                if where[1][1]<self.low: self.low = where[1][1]
                if where[1][1]>self.high: self.high = where[1][1]

                #if pos>length: 
                #     print('at end!',pos,length,bend)
                #     if bend==0:
                #         x1 = where[1][0]-12*orientation
                #         y1 = where[1][1]+5*orientation
                #         x2 = x_max+20*orientation
                #         y2 = y2+30*orientation
                #         bezierX = x2
                #         bezierY = (y1+y2)/2
                #         points = "M "+str(x1)+" "+str(y1)+" Q"+str(bezierX)+" "+str(bezierY)+" "+str(x2)+" "+str(y2)
                #         pos=0
                #         length = self.lengthbezier([x1,y1],[bezierX,bezierY],[x2,y2],0.001)
                #         #self.output += "<path d='" + points + "' stroke='black' fill='none' stroke-width='2'  class='"+name+" long'/>"
                #     else:
                #         y1 = where[1][1]+between_residues*orientation
                #         x1 = where[1][0]
                #         if abs(x1-self.maxX['left'])>abs(x1-self.maxX['right']):
                #             x1 = where[1][0]-5*orientation
                #             x2 = self.maxX['left']+30
                #         else:
                #             x1 = where[1][0]+5*orientation
                #             x2 = self.maxX['right']-30

                #         y2 = y2+35*orientation
                #         bezierX = x1
                #         bezierY = y2+20*orientation

                #         bezierX2 = x2
                #         bezierY2 = y2-40*orientation

                #         length = self.lengthbezier([x1,y1],[bezierX,bezierY],[bezierX2,bezierY2],0.001,[x2,y2])
                #         points = "M "+str(x1)+","+str(y1)+" C"+str(bezierX)+","+str(bezierY)+" "+str(bezierX2)+","+str(bezierY2)+" "+str(x2)+","+str(y2)
                #         #self.output += "<path d='" + points + "' stroke='black' fill='none' stroke-width='2'  class='"+name+" long'/>"
                #         pos = 0

                    #bend +=1

            self.output += "<rect onclick='toggleLoop(\"."+name+"\",\"long\");' class='"+name+" long' x="+str(self.TBCoords[linked_helix][position][0]-40*orientation-25)+" y="+str((labely+self.TBCoords[linked_helix][position][1])/2-13)+" rx=5 ry=5 width='50' height='20' stroke='black' fill='white' stroke-width='1' style2='fill:red;stroke:black;stroke-width:5;opacity:0.5'/>"
            self.output += str("<text onclick='toggleLoop(\"."+name+"\",\"long\");' class='"+name+" long' x="+str(self.TBCoords[linked_helix][position][0]-40*orientation)+" y="+str((labely+self.TBCoords[linked_helix][position][1])/2)+" text-anchor='middle' font-size="+str(font_size)+" font-family='"+font_family+"'>"+name+"</text>")







    def drawSnakePlotLoops(self):

        y_offset = 50
        font_size = 12
        font_family = 'courier'
        bezier_pull = 80
        orientation = 1
        for i in range(1,7):
            number = round(0.01+i/2) #hacky way of getting # of loop intra/extra (1 to 3)
            if i%2==0: 
                position = 'extra' #is loop intra- or extrascelluar
                name = "ECL"+str(number)
                orientation = -1
            else:
                position = 'intra'
                orientation = 1
                name = "ICL"+str(number)
            #print('Loop',i,position,number,orientation)

            #Get positions of two  linking residues from each helix
            x1 = self.TBCoords[i][position][0]
            y1 = self.TBCoords[i][position][1]
            x2 = self.TBCoords[i+1][position][0]
            y2 = self.TBCoords[i+1][position][1]

            boxX = (x1+x2)/2 #midway between
            if position=='extra': 
                boxY = min(y1,y2)-y_offset #over helix
                y_indent = -1*bezier_pull
            if position=='intra': 
                boxY = max(y1,y2)+y_offset #over helix
                y_indent = bezier_pull

            points = str(x1)+","+str(y1)+" "+str(boxX)+","+str(boxY)+" "+str(x2)+","+str(y2)
            points2 = "M "+str(x1)+" "+str(y1)+" Q"+str(boxX)+" "+str(boxY+y_indent)+" "+str(x2)+" "+str(y2)


            #Getting midpoint of Bezier curve http://www.svgbasics.com/curves.html
            Dx = ((x1+boxX)/2)
            Ex = ((x2+boxX)/2)
            Fx = (Dx+Ex)/2

            Dy = ((y1+boxY+y_indent)/2)
            Ey = ((y2+boxY+y_indent)/2)
            Fy = (Dy+Ey)/2

            #JUST SIMPLE
            self.output += "<path class='"+name+" short' d='" + points2 + "' stroke='black' fill='none' stroke-width='2' />"
            self.output += "<rect onclick='toggleLoop(\"."+name+"\",\"short\");' class='"+name+" short' x="+str(Fx-18)+" y="+str(Fy-13)+" rx=5 ry=5 width='35' height='20' stroke='black' fill='white' stroke-width='1' style2='fill:red;stroke:black;stroke-width:5;opacity:0.5'/>"
            self.output += str("<text  onclick='toggleLoop(\"."+name+"\",\"short\");' class='"+name+" short' x="+str(Fx)+" y="+str(Fy)+" text-anchor='middle' font-size="+str(font_size)+" font-family='"+font_family+"'>"+name+"</text>")


            if name not in self.segments: continue
            rs = self.segments[name] #get residues
            #print("residues in ",name,len(rs))

            y_indent = y_indent*len(rs)/5 #get an approx need for y_indent for size of loop


            loop_long_length = 0
            super_loop_long_length = 40
            if len(rs)<loop_long_length:
                between_residues = 18
            else:
                between_residues = 18

            length_of_residues_in_loop = len(rs)*between_residues-self.residue_radius
            if len(rs)<loop_long_length:
                length = self.lengthbezier([x1,y1],[boxX,boxY+y_indent],[x2,y2],0.001)
            else:
                length = self.lengthbezier([x1,y1],[x1-abs(y_indent)*0.5,boxY+y_indent*0.5],[x2+abs(y_indent)*0.5,boxY+y_indent*0.5],0.001,[x2,y2])


            if len(rs)<super_loop_long_length:
                tries = 0 #adjust size
                while abs(length-length_of_residues_in_loop-70)>5:
                    #print(abs(length-length_of_residues_in_loop+100),length,length_of_residues_in_loop,tries)
                    if length-length_of_residues_in_loop-70>5:
                        y_indent *=0.9
                    else:
                        y_indent *=1.1
                    if len(rs)<loop_long_length:
                        length = self.lengthbezier([x1,y1],[boxX,boxY+y_indent],[x2,y2],0.001)
                    else:
                        length = self.lengthbezier([x1,y1],[x1-abs(y_indent)*0.5,boxY+y_indent*0.5],[x2+abs(y_indent)*0.5,boxY+y_indent*0.5],0.001,[x2,y2])

                    tries += 1
                    if tries>100:
                        break


            

            pos = (length-length_of_residues_in_loop)/2 #get start pos

            indentX = 0
            indentY2 = 0
            prev_where = [x1,y1]
            if len(rs)>=super_loop_long_length: #to make wrapped

                first_bend = round(len(rs)/2)
                first_bend_x = x1
                bend_middle = round((x2+x1)/2)
                first_bend_y = y1+orientation*(first_bend+4)*between_residues*0.8

                second_bend = round(len(rs)/2)

                if orientation==-1: #indent more if ECL
                    x_left = 150
                else:
                    x_left = 30

                bends = 1
                tries = 0
                length = 0
                distance_between_rows = between_residues*1.7
                temp_max_y = self.maxY[position]
               # print("test",orientation,temp_max_y,y1,y2)
                if orientation==1 and (temp_max_y<y1 or temp_max_y<y2):
                    temp_max_y = max(y1,y2)
                elif orientation==-1 and (temp_max_y>y1 or temp_max_y>y2):
                    temp_max_y = min(y1,y2)
                #print("test",orientation,temp_max_y,y1,y2)

                while abs(length-length_of_residues_in_loop)>6: #determine length of bends etc depending on amount of loops
                    tries +=1
                    length_first = self.lengthbezier([x1,y1],[x1+60,temp_max_y+80*orientation],[x_left,temp_max_y+80*orientation],0.001)-60
                    #length_first = floor(length_first / between_residues)*between_residues

                    length_bend = (bends*2+1)*between_residues*2

                    length_middel = (x2-x_left-80)*(bends*2+1)
                    length_middel = floor(length_middel / between_residues)*between_residues

                    length_second = self.lengthbezier([x2-between_residues-30,temp_max_y+80*orientation+(bends*2+1)*distance_between_rows*orientation],[x2+50,temp_max_y+80*orientation+(bends*2+1)*distance_between_rows*orientation],[x2,y2],0.001)-40


                    #length_second = floor(length_second / between_residues)*between_residues

                    length = length_first+length_second+length_bend+length_middel
                    #print(tries,'length',length,length_of_residues_in_loop)

                    if length-length_of_residues_in_loop>6:
                        x_left += 0.1*(length-length_of_residues_in_loop)
                    else:
                        if (orientation==1 and x_left<30) or (orientation==-1 and x_left<150):
                            bends +=1
                            #print('add bend!',tries)
                        else:
                            x_left += 0.1*(length-length_of_residues_in_loop)
                    if tries>30:
                        break


                #print('tries',tries,'x_left',x_left,'bends',bends)

                #pos = (length-length_of_residues_in_loop)/2 #get start pos

                pos = 60

                points2 = "M "+str(x1)+" "+str(y1)+" Q"+str(x1+60)+" "+str(temp_max_y+80*orientation)+" "+str(x_left)+" "+str(temp_max_y+80*orientation )
                self.output += "<path class='"+name+" long' d='" + points2 + "' stroke='black' fill='none' stroke-width='2' />"


                #for bend in range(1,2+(bends*2)):
                    #print(bend)
                    #self.output += "<line class='"+name+" long' x1="+str(x_left)+" y1="+str(temp_max_y+80*orientation+bend*distance_between_rows*orientation)+" x2="+str(x2-between_residues-40)+" y2="+str(temp_max_y+80*orientation+bend*distance_between_rows*orientation)+" stroke='black' fill='none' stroke-width='2' stroke-dasharray2='1,1' />"

                pos_bend = 0
                bend = 1
                bend_direction = 1
                pos_last = 0
                for i in range(0,len(rs)):
                    r = rs[i]
                    if pos<=length_first+61: #first branch
                        where = self.wherebezier([x1,y1],[x1+60,temp_max_y+80*orientation],[x_left,temp_max_y+80*orientation],0.001,pos)
                        pos += ((length_first)/floor((length_first)/between_residues))
                        #print(i,pos,length_first)
                    elif (bend/2)==(bends+1): #lastpart
                        #if bends!=0 and pos_last==0:
                            #last_bend_y = last_bend_y-orientation*distance_between_rows/4
                        if pos_last==0:
                            length_second = self.lengthbezier([last_bend_x+between_residues,last_bend_y],[x2+100,temp_max_y+80],[x2,y2],0.001)
                            res_left = len(rs)-i
                            #print('length',length_second,'res lef',res_left)
                            points2 = "M "+str(last_bend_x+between_residues)+" "+str(last_bend_y)+" Q"+str(x2+50)+" "+str(last_bend_y)+" "+str(x2)+" "+str(y2)
                            self.output += "<path class='"+name+" long' d='" + points2 + "' stroke='black' fill='none' stroke-width='2' />"

                        where = self.wherebezier([last_bend_x+between_residues,last_bend_y],[x2+50,last_bend_y],[x2,y2],0.001,pos_last)

                        #pos_last += between_residues
                        #pos_last += (length_second-40)/res_left
                        pos_last += between_residues
                        #print(i,'length',length_second,'res lef',res_left, 'pos',pos_last,last_bend_y)
                    else:
                        #if 
                        if pos_bend==0: #if first residue in line put in middle
                            where[1][0] = where[1][0]-between_residues*bend_direction
                            #where[1][0] = where[1][0]
                            where[1][1] = where[1][1]+orientation*distance_between_rows/2
                        # elif pos_bend==between_residues: #if 2nd residue in line put in middle
                        #     #where[1][0] = where[1][0]-between_residues*bend_direction
                        #     where[1][0] = where[1][0]
                        #     where[1][1] = temp_max_y+80+bend*distance_between_rows
                        else:
                            where[1][0] = where[1][0]+between_residues*bend_direction
                            where[1][1] = temp_max_y+80*orientation+bend*distance_between_rows*orientation
                        last_bend_x = where[1][0]
                        last_bend_y = where[1][1]

                        pos_bend += between_residues

                        if pos_bend>=(x2-x_left-40): #no more bend left
                            bend +=1
                            pos_bend = 0
                            if bend_direction==1: 
                                bend_direction = -1
                            elif bend_direction==-1: 
                                bend_direction = 1
                    self.output += self.DrawResidue(where[1][0],where[1][1],r[1], where[1][0], r[3], self.residue_radius-1,name+" long")


                    if orientation==-1: 
                        if where[1][1]<self.maxY[position]: self.maxY[position] = where[1][1]
                    else:
                        if where[1][1]>self.maxY[position]: self.maxY[position] = where[1][1]


                    if where[1][1]>self.high: self.high = where[1][1]
                    if where[1][1]<self.low: self.low = where[1][1]


                box_y = temp_max_y+80*orientation+bend*distance_between_rows*orientation+5*orientation

                self.output += "<rect onclick='toggleLoop(\"."+name+"\",\"long\");' class='"+name+" long' x="+str((x2+x1)/2-18)+" y="+str(box_y-13)+" rx=5 ry=5 width='35' height='20' stroke='black' fill='white' stroke-width='1' style2='fill:red;stroke:black;stroke-width:5;opacity:0.5'/>"
                self.output += str("<text  onclick='toggleLoop(\"."+name+"\",\"long\");' class='"+name+" long' x="+str((x2+x1)/2)+" y="+str(box_y)+" text-anchor='middle' font-size="+str(font_size)+" font-family='"+font_family+"'>"+name+"</text>")


                if box_y>self.high: self.high = box_y
                if box_y<self.low: self.low = box_y




                # if first_bend_y>self.high: self.high = first_bend_y
                # if first_bend_y<self.low: self.low = first_bend_y

                # third_bend = len(rs)-first_bend
                # bezier1 = [x1-self.residue_radius,y1+40*orientation]
                # bezier2 = [x1-self.residue_radius*10,first_bend_y]
                # bezier3 = [x1+50+self.residue_radius*2,first_bend_y]
                # bezier4 = [bend_middle-self.residue_radius*2,y1+40*orientation]
                # length =  self.lengthbezier(bezier1,bezier2,bezier3,0.001,bezier4)
                # for i in range(0,first_bend):
                #     r = rs[i]
                #     #x = x1-((first_bend/2)-abs(i-first_bend/2))*2
                #     xy = self.wherebezier(bezier1,bezier2,bezier3,0.001,i*length/first_bend,bezier4)

                #     if i==0: self.traceoutput+= "<line class='"+name+" long' x1="+str(x1)+" y1="+str(y1)+" x2="+str(xy[1][0])+" y2="+str(xy[1][1])+" stroke='black' fill='none' stroke-width='2' stroke-dasharray2='1,1' />"
                #     self.output += self.DrawResidue(xy[1][0],xy[1][1],r[1], r[0], r[0], self.residue_radius,name+" long")
                #     first_bend_max_y = xy[1][1]
                #     first_bend_max_x = xy[1][0]


                # bezier1 = [first_bend_max_x+self.residue_radius*3,first_bend_max_y]
                # bezier2 = [first_bend_max_x,first_bend_y]
                # bezier3 = [x2+50+self.residue_radius*5,first_bend_y]
                # bezier4 = [x2,y2+40*orientation]
                # length =  self.lengthbezier(bezier1,bezier2,bezier3,0.001,bezier4)
                # for i in range(0,len(rs)-first_bend):
                #     r = rs[i+first_bend]
                #     #x = x1-((first_bend/2)-abs(i-first_bend/2))*2
                #     xy = self.wherebezier(bezier1,bezier2,bezier3,0.001,i*length/first_bend,bezier4)

                #     if i==0: self.traceoutput+= "<line class='"+name+" long' x1="+str(first_bend_max_x)+" y1="+str(first_bend_max_y)+" x2="+str(xy[1][0])+" y2="+str(xy[1][1])+" stroke='black' fill='none' stroke-width='2' stroke-dasharray2='1,1' />"
                #     if i==len(rs)-first_bend-1: self.traceoutput+= "<line class='"+name+" long' x1="+str(x2)+" y1="+str(y2)+" x2="+str(xy[1][0])+" y2="+str(xy[1][1])+" stroke='black' fill='none' stroke-width='2' stroke-dasharray2='1,1' />"
                #     self.output += self.DrawResidue(xy[1][0],xy[1][1],r[1], r[0], r[0], self.residue_radius,name+" long")
                #     if xy[1][1]>first_bend_max_y: 
                #         first_bend_max_y = xy[1][1]
                #         x_at_first_bend_max_y = xy[1][0]
                #     first_bend_max_x = xy[1][0]


                # self.output += "<rect onclick='toggleLoop(\"."+name+"\",\"long\");' class='"+name+" long' x="+str((x2+x1)/2-18)+" y="+str(first_bend_max_y-13)+" rx=5 ry=5 width='35' height='20' stroke='black' fill='white' stroke-width='1' style2='fill:red;stroke:black;stroke-width:5;opacity:0.5'/>"
                # self.output += str("<text  onclick='toggleLoop(\"."+name+"\",\"long\");' class='"+name+" long' x="+str((x2+x1)/2)+" y="+str(first_bend_max_y)+" text-anchor='middle' font-size="+str(font_size)+" font-family='"+font_family+"'>"+name+"</text>")


                # if orientation==-1: 
                #     if first_bend_max_y<self.maxY[position]: self.maxY[position] = first_bend_max_y
                # else:
                #     if first_bend_max_y>self.maxY[position]: self.maxY[position] = first_bend_max_y


            else: #make rounded arc
                points2 = "M "+str(x1)+" "+str(y1)+" Q"+str(boxX)+" "+str(boxY+y_indent)+" "+str(x2)+" "+str(y2)
                labelbox = self.wherebezier([x1,y1],[boxX,boxY+y_indent],[x2,y2],0.001,length/2)

                if len(rs)>loop_long_length: 
                    points2 = "M "+str(x1)+","+str(y1)+" C"+str(x1-abs(y_indent)*0.5)+","+str(boxY+y_indent*0.5)+" "+str(x2+abs(y_indent)*0.5)+","+str(boxY+y_indent*0.5)+" "+str(x2)+","+str(y2)
                    labelbox = self.wherebezier([x1,y1],[x1-abs(y_indent)*0.5,boxY+y_indent*0.5],[x2+abs(y_indent)*0.5,boxY+y_indent*0.5],0.001,length/2,[x2,y2] )
                
                labelbox[1][1] += orientation*40

                self.output += "<path class='"+name+" long' d='" + points2 + "' stroke='black' fill='none' stroke-width='2' />"


                max_y = y1
                for i in range(0,len(rs)):
                    r = rs[i]
                    if len(rs)>=loop_long_length:
                        where = self.wherebezier([x1,y1],[x1-abs(y_indent)*0.5,boxY+y_indent*0.5],[x2+abs(y_indent)*0.5,boxY+y_indent*0.5],0.001,pos,[x2,y2] )
                    else:
                        where = self.wherebezier([x1,y1],[boxX,boxY+y_indent],[x2,y2],0.001,pos)

                    self.output += self.DrawResidue(where[1][0],where[1][1],r[1], r[0], r[3], self.residue_radius-1,name+" long")
                    pos += between_residues

                    if where[1][1]>self.high: self.high = where[1][1]
                    if where[1][1]<self.low: self.low = where[1][1]
                    prev_where = where[1][0],where[1][1]
                    
                    if orientation==-1: 
                        if where[1][1]<self.maxY[position]: self.maxY[position] = where[1][1]
                    else:
                        if where[1][1]>self.maxY[position]: self.maxY[position] = where[1][1]

                    if orientation==-1: 
                        if where[1][1]<max_y: 
                            max_y = where[1][1]
                            x_at_max_y = where[1][0]
                    else:
                        if where[1][1]>max_y: 
                            max_y = where[1][1]
                            x_at_max_y = where[1][0]

                    #print('low',self.low,'high',self.high)
                if orientation==1: 
                    max_y = max_y+25
                else:
                    max_y = max_y-20
                self.output += "<rect onclick='toggleLoop(\"."+name+"\",\"long\");' class='"+name+" long' x="+str(x_at_max_y-18)+" y="+str(max_y-13)+" rx=5 ry=5 width='35' height='20' stroke='black' fill='white' stroke-width='1' style2='fill:red;stroke:black;stroke-width:5;opacity:0.5'/>"
                self.output += str("<text  onclick='toggleLoop(\"."+name+"\",\"long\");' class='"+name+" long' x="+str(x_at_max_y)+" y="+str(max_y)+" text-anchor='middle' font-size="+str(font_size)+" font-family='"+font_family+"'>"+name+"</text>")







class DrawHelixBox(Diagram):

    plot_data = {}
    plot_data['direction'] = [0,0, 1, 0, 1, 0, 1, 0]; # 0: EC->IC, 1: IC->EC
    plot_data['helixRadius'] = 70;
    # Class A
    plot_data['Class A'] = {}
    plot_data['Class A']['coordinates'] = [0,[455,240],[385,108],[245,118],[105,95],[75,235],[185,320],[324,303]]
    plot_data['Class A']['helixTopResidues'] = [0,'1x32', '2x63', '3x26', '4x61', '5x39', '6x57', '7x32']
    plot_data['Class A']['helixTopResidues'] = [0,32, 63, 26, 61, 39, 57, 32]
    plot_data['Class A']['rotation'] = [0,340, 320, 290, 125, 40, 180, 130] # in degrees

    # Class C
    plot_data['Class C'] = {}
    plot_data['Class C']['coordinates'] = [0, [455,231],[390,108],[245,118],[105,105],[75,241],[193,320],[328,303]]
    plot_data['Class C']['helixTopResidues'] = [0, 34, 61, 26, 61, 38, 57, 35]
    plot_data['Class C']['rotation'] = [0, 170, 200, 290, 145, 250, 210, 310] # in degrees


    def __init__(self, residue_list, protein_class,protein_name, nobuttons = None):
        self.nobuttons = nobuttons
        self.receptorId = protein_name
        self.family = protein_class

        self.sequence = residue_list

        #self.receptorId = protein
        #self.family = protein.get_protein_class()
        self.output = ''
        self.type = 'helixbox'

        # Use class A as the default for now FIXME add all classes
        if self.family not in self.plot_data:
            self.family = 'Class A'

        segment_lists = {}
        for r in residue_list:
            if r.protein_segment:
                if r.protein_segment.slug not in segment_lists:
                    segment_lists[r.protein_segment.slug] = []

                segment_lists[r.protein_segment.slug].append(r)
            elif r.segment_slug: #from aligment
                if r.segment_slug not in segment_lists:
                    segment_lists[r.segment_slug] = []

                segment_lists[r.segment_slug].append(r)



        for i in range(1,len(self.plot_data[self.family]['coordinates'])):
            #fetch residues | add sort by sequence_number FIXME
            # self.residuelist = residue_list.filter(
            #     protein_segment__slug='TM'+str(i)).prefetch_related('display_generic_number','generic_number')


            try:

                self.residuelist = segment_lists['TM'+str(i)]

                self.output += self.DrawHelix(self.plot_data[self.family]['coordinates'][i][0],
                    self.plot_data[self.family]['coordinates'][i][1],
                    self.residuelist,
                    self.plot_data['helixRadius'],
                    self.plot_data['direction'][i],
                    i,
                    self.plot_data[self.family]['helixTopResidues'][i],
                    self.plot_data[self.family]['rotation'][i]
                    )
            except:
                pass




    def __str__(self):  
        return mark_safe(self.create(self.output+self.drawToolTip(),595,430,"helixbox", self.nobuttons))

    def DrawHelix(self, startX,startY,residuelist,radius,direction,helixNum,helixTopResidue,rotation):

        sequence = {}

        for r in residuelist:
            displaylabel = r.amino_acid+str(r.sequence_number)
            generic_number = ''
            if r.generic_number: 
                generic_number = r.generic_number.label
            elif r.family_generic_number:
                generic_number = r.family_generic_number
            if r.display_generic_number: displaylabel += "\n"+r.display_generic_number.label
            if hasattr(r, 'extra'): displaylabel += "\n" + r.extra
            sequence[int(generic_number[2:])] = {'residueType':r.amino_acid,'residueNumber':r.sequence_number,'generic_number':generic_number,'displaylabel':displaylabel}

        # box size
        numResPerSide = 5
        numResInBox = numResPerSide*4
        residueRadius = 12
        
        # start positions of the four sides
        output_residue = ""

        helixSideCoord = {}

        for i in range(1,5):
            helixSideCoord[i] = {}
            helixSideCoord[i]['x'] = startX + radius * cos( self.deg2rad((i-1)*90+rotation) )
            helixSideCoord[i]['y'] = startY + radius * sin( self.deg2rad((i-1)*90+rotation) )

        # starting side
        helixSide = 4 # start on the last side of the helix

        # residue position incrementer
        resPosIncr = 1

        # helix direction indicator
        helixDirection = 1
        if helixNum % 2 != 0:
            helixDirection = -1

        # init residue number (draw lowest residue first)
        currentResidue = helixTopResidue - helixDirection * (numResInBox - 1)

        coordinates = {}

        for i in range(1,numResInBox+1):
            
            # next helix side
            if helixSide == 1:
                # go back to side 1
                nextHelixSide = 4
            else:
                # next side
                nextHelixSide = helixSide - 1

            # find number for next residue (for bulge assignment)
            nextResidue = currentResidue + helixDirection

            # line from the current side to the next
            lineEquation = self.LineEquation(
                {
                    "x":helixSideCoord[helixSide]["x"],
                    "y":helixSideCoord[helixSide]["y"]},
                {
                    "x":helixSideCoord[nextHelixSide]["x"],
                    "y":helixSideCoord[nextHelixSide]["y"]})

            # direction of perpendicular move (for bulges), depends on line slope
            perpDir = -1
            if lineEquation["m"] < 0:
                perpDir = 1

            # length of perpendicular move (for bulges), depends on line slope
            perpLen = 5
            if lineEquation["m"] > 1 and lineEquation["x"] > 0:
                perpLen = 15

            x = {}
            y = {}
            coordinates[i] = {}
            # calculate coordinates of the residue (and save them for backbone drawing)
            move = self.MoveAlongLine(residueRadius*1.4, lineEquation['m'], False, lineEquation['x'],
                lineEquation['y'])
            x['0'] = coordinates[i]["x"] = helixSideCoord[helixSide]["x"] + resPosIncr*move["x"]
            y['0'] = coordinates[i]["y"] = helixSideCoord[helixSide]["y"] + resPosIncr*move["y"]

            # init array for residues to be drawn in this position (can be more than on in a bulge)
            coordinateIndices = []
            if currentResidue in sequence.keys():
                coordinateIndices = ['0']

            # check for bulges (residue number suffixed with 1) or constrictions (missing
            # residue number)
            if int(str(nextResidue)+"1") in sequence:
                coordinateIndices.append('1')
                perpMove = self.MoveAlongLine(perpLen, lineEquation["m"], True, lineEquation['x'],
                    lineEquation['y']);
                x['1'] = (helixSideCoord[helixSide]["x"] + (resPosIncr+0.6)*move["x"] +
                     resPosIncr*perpDir*perpMove["x"])
                y['1'] = (helixSideCoord[helixSide]["y"] + (resPosIncr+0.6)*move["y"] +
                     resPosIncr*perpDir*perpMove["y"])
            
            if coordinateIndices: #not empty
                for coordinateIndex in coordinateIndices:
                    tempCurrentResidue = currentResidue;
                    if coordinateIndex=='1': #not empty
                        tempCurrentResidue = int(str(nextResidue)+str(coordinateIndex))

                    # Get label information of each residue.
                    residue_number = sequence[tempCurrentResidue]['residueNumber'];
                    label = sequence[tempCurrentResidue]['displaylabel']
                    #label = self::getResidueLabel(receptorId, helixNum, residue_number); #FIXME IMPLEMENT
                    #label = "m: " . lineEquation["m"] . " x: " . lineEquation["x"];
                    
                    # draw the residue
                    output_residue += self.DrawResidue(x[coordinateIndex],y[coordinateIndex],
                        sequence[tempCurrentResidue]['residueType'],residue_number, label,residueRadius);
                
            # residue position incrementer
            if i % 4 == 0:
                resPosIncr += 1

            # increment side
            helixSide = nextHelixSide

            # next residue
            currentResidue = nextResidue
        
        output_backbone = self.DrawBackbone(coordinates)

        helix_number_svg = "<text x='"+str(startX)+"' y='"+str(startY+7)+"' text-anchor='middle' font-family='helvetica' font-size='20'>"+str(helixNum)+"</text>\n"

        return output_backbone+output_residue+helix_number_svg
