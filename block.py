from cells import SwitchCell,TrackCellColors,TrackCellType
from mrbusUtils import MRBusBit,MRBusPacket
import datetime
import re
from cells import TrackCell, TrackCellColors, TrackCellType

def relCoord(base_x, newVal):
  newVal = str(newVal)
  m = re.match('^\+([0-9].*)', newVal)
  if m is not None:
    retval = base_x + int(m.group(0))
    #print("relCoord pos base=%d newVal=[%s] newval=%d" % (base_x, newVal, retval))
    return retval

  m = re.match('^\-([0-9].*)', newVal)
  if m is not None:
    retval = base_x + int(m.group(0))
    #print("relCoord neg base=%d newVal=[%s] newval=%d" % (base_x, newVal, retval))
    return retval
  
  return int(newVal)

class Block:
  def __init__(self, config, txCallback, cellXY):
    self.name = config['name']
    self.type = config['type']
    self.manualControl = False
    self.occupied = False
    self.powerOn = True
    self.locked = False
    self.lined = False
    self.leftAdjoiningBlockName = ""
    self.rightAdjoiningBlockName = ""
    self.lastUpdated = datetime.datetime.now() - datetime.timedelta(days=30)  # just make this way in the past
    self.txCallback = txCallback
    self.base_x = 0
    self.base_y = 0
    self.cellXY = cellXY
    self.linedCells = [ ]
    self.cp = None
    
    if "leftAdjoiningBlockName" in config.keys():
      self.leftAdjoiningBlockName = config['leftAdjoiningBlockName']

    if "rightAdjoiningBlockName" in config.keys():
      self.rightAdjoiningBlockName = config['rightAdjoiningBlockName']
    
    
    pattern = ""
    if "sensorManual" in config.keys():
      pattern = config['sensorManual']
    self.sensorManual = MRBusBit(pattern)

    pattern = ""
    if "sensorOccupancy" in config.keys():
      pattern = config['sensorOccupancy']
    self.sensorOccupancy = MRBusBit(pattern)

    pattern = ""
    if "sensorPower" in config.keys():
      pattern = config['sensorPower']
    self.sensorPower = MRBusBit(pattern, True)

    self.cells = [ ]
    if "base_x" in config.keys():
      self.base_x = int(config['base_x'])

    if "base_y" in config.keys():
      self.base_y = int(config['base_y'])

    for cell in config['cells']:
      x = relCoord(self.base_x, cell['x'])
      y = relCoord(self.base_y, cell['y'])

      if 'x_end' in cell.keys():
        x_end = relCoord(self.base_x, cell['x_end']) + 1
      else:
        x_end = x + 1

      if 'y_end' in cell.keys():
        y_end = relCoord(self.base_x, cell['y_end']) + 1
      else:
        y_end = y + 1

      for cell_x in range(x, x_end):
        for cell_y in range(y, y_end):
          newCell = TrackCell()
          cellType = {
            'horiz':TrackCellType.HORIZONTAL,
            'diag_right_up':TrackCellType.DIAG_RIGHT_UP,
            'diag_left_up':TrackCellType.DIAG_LEFT_UP,
            'angle_left_down':TrackCellType.ANGLE_LEFT_DOWN,
            'angle_left_up':TrackCellType.ANGLE_LEFT_UP,
            'angle_right_down':TrackCellType.ANGLE_RIGHT_DOWN,
            'angle_right_up':TrackCellType.ANGLE_RIGHT_UP,
            'horiz_rightgap':TrackCellType.END_HORIZ_RIGHT,
            'horiz_leftgap':TrackCellType.END_HORIZ_LEFT,
          }
          newCell.setOwner(self)
          newCell.setXY(cell_x, cell_y)
          if cell['type'] in cellType.keys():
            print("Placing cell of type [%s] at (%d,%d)" % (cell['type'], cell_x, cell_y))
            newCell.setType(cellType[cell['type']])
          else:
            print("Warnings - cell type %s not known at (%d,%d)" % (cell['type'], x, y))

          self.cells.append(newCell)
          #self.cellXY[(x,y)] = newCell

  # processPacket takes an incoming MRBus packet
  def processPacket(self, pkt):
#    print("Block [%s] processing packet [%s]"% (self.name, pkt))
    changed = self.sensorManual.testPacket(pkt)
    changed = self.sensorOccupancy.testPacket(pkt) or changed
    changed = self.sensorPower.testPacket(pkt) or changed

    if changed:
#      print("Packet changed block")
      self.manualControl = self.sensorManual.getState()
      self.occupied = self.sensorOccupancy.getState()
      self.powerOn = self.sensorPower.getState()
      self.recalculateState()

  def isOccupied(self):
    return self.occupied

  def isManual(self):
    return self.manualControl

  def setRoute(self, leftBound=False, startX=0, startY=0):
    if self.occupied:  # can't route through an occupied block
      return ""
    
    self.lined = True
    self.linedLeftBound = leftBound
    
    if self.cp:
      self.linedCells = [ ]
      nextBlockName = self.routeTracer(startX, startY, leftBound)
    else:  # If we're not a control point, all cells are lined
      self.linedCells = self.cells
      if self.linedLeftBound:
        nextBlockName = self.leftAdjoiningBlockName
        #print("Left 2 adjoining block name [%s]" % (nextBlockName))
      else:
        nextBlockName = self.rightAdjoiningBlockName
        #print("Right 2 adjoining block name [%s]" % (nextBlockName))
    self.recalculateState()
    return nextBlockName
  
  def clearRoute(self):
    if self.occupied or not self.lined:
      return

    self.lined = False

    if self.cp:
      if self.linedLeftBound:
        x = 16000;
        y = 16000;

        for cell in self.linedCells:
          if cell.cell_x < x:
            x = cell.cell_x
            y = cell.cell_y

        if (x-1,y) in self.cellXY.keys():
          #print("Looking for next block at %d/%d" % (x-1, y))
          nextBlockCell = self.cellXY[(x-1,y)]
          nextBlockName = nextBlockCell.owner.name
          #print("Left adjoining block name [%s]" % (nextBlockName))
      else: # rightbound
        x = 0;
        y = 0;

        for cell in self.linedCells:
          if cell.cell_x >= x:
            x = cell.cell_x
            y = cell.cell_y

        if (x+1,y) in self.cellXY.keys():
          #print("Looking for next block at %d/%d" % (x+1, y))
          nextBlockCell = self.cellXY[(x+1,y)]
          nextBlockName = nextBlockCell.owner.name
          #print("Right adjoining block name [%s]" % (nextBlockName))
    else:  # Not a control point, just a block
      if self.linedLeftBound:
        nextBlockName = self.leftAdjoiningBlockName
        #print("Left 2 adjoining block name [%s]" % (nextBlockName))
      else:
        nextBlockName = self.rightAdjoiningBlockName
        #print("Right 2 adjoining block name [%s]" % (nextBlockName))
    self.linedCells = [ ]
    self.recalculateState()
    return nextBlockName

  def assocControlPoint(self, controlPoint):
    self.cp = controlPoint
    print("Block [%s] has associated with CP [%s]" % (self.name, self.cp.name))

  def onLeftClick(self):
    return False  # Blocks don't respond to clicks

  def recalculateState(self):
    print("Recalculating state for [%s]" % (self.name))
    trackColor = TrackCellColors.getColor('track_unknown')

    # Compute track color
    
    if not self.powerOn:
      trackColor = TrackCellColors.getColor('track_nopower')
    elif self.occupied:
      trackColor = TrackCellColors.getColor('track_occupied')
      self.lined = False  # if we're occupied, we can't be lined
    elif self.lined:
      trackColor = TrackCellColors.getColor('track_lined')
    elif self.manualControl:
      trackColor = TrackCellColors.getColor('track_manual')
    else:
      trackColor = TrackCellColors.getColor('track_idle')

    for i in range(0, len(self.cells)):
      if self.cp and trackColor == TrackCellColors.getColor('track_lined'):
        # only make the traced cells lined
        if self.cells[i] in self.linedCells:
          self.cells[i].setColor(trackColor)
        else:
          self.cells[i].setColor(TrackCellColors.getColor('track_idle'))
      else:
        self.cells[i].setColor(trackColor)

  def routeTracer(self, startX, startY, walkLeft):
    x = startX
    y = startY
    
    #print("Tracing route squirrel - startx=%d starty=%d" % (x,y))
    # From our current point, we need to walk left or right 
    # until we hit the end of the CP

    try:
      nextBlock = None
      stillWalking = True
      while(stillWalking):

        if (x,y) not in self.cellXY.keys():
          #print("x=%d y=%d not in cellXY keys, ending" % (x, y))
          stillWalking = False
          break

        cell = self.cellXY[(x,y)]
        if walkLeft:
          #print("Walking left - x=%d, y=%d, type=%s" % (x, y, cell.trackType))

          if cell.trackType == TrackCellType.HORIZONTAL:
            self.linedCells.append(cell)
            x = x - 1
            
          elif cell.trackType == TrackCellType.END_HORIZ_RIGHT:
            self.linedCells.append(cell)
            x = x - 1

          elif cell.trackType == TrackCellType.END_HORIZ_LEFT:
            self.linedCells.append(cell)
            
            if (x-1,y) in self.cellXY.keys():
              #print("Looking for next block at %d/%d" % (x-1, y))
              nextBlockCell = self.cellXY[(x-1,y)]
              nextBlock = nextBlockCell.owner.name
            else:
              pass
              #print("No next block at %d/%d" % (x-1, y))
            stillWalking = False # terminate walking

          elif cell.trackType == TrackCellType.DIAG_LEFT_UP:
            self.linedCells.append(cell)
            x = x - 1
            y = y - 1

          elif cell.trackType == TrackCellType.DIAG_RIGHT_UP:
            self.linedCells.append(cell)
            x = x - 1
            y = y + 1

          elif cell.trackType == TrackCellType.ANGLE_LEFT_UP:
            self.linedCells.append(cell)
            x = x - 1
            y = y - 1

          elif cell.trackType == TrackCellType.ANGLE_LEFT_DOWN:
            self.linedCells.append(cell)
            x = x - 1
            y = y + 1

          elif cell.trackType == TrackCellType.ANGLE_RIGHT_UP:
            self.linedCells.append(cell)
            x = x - 1

          elif cell.trackType == TrackCellType.ANGLE_RIGHT_DOWN:
            self.linedCells.append(cell)
            x = x - 1

          elif cell.trackType == TrackCellType.SWITCH_RIGHT_UP:
            self.linedCells.append(cell)
            x = x - 1 

          elif cell.trackType == TrackCellType.SWITCH_RIGHT_DOWN:
            self.linedCells.append(cell)
            x = x - 1

          elif cell.trackType == TrackCellType.SWITCH_LEFT_UP:
            self.linedCells.append(cell)
            x = x - 1 
            if cell.getSwitchPosition() != 0:
              y = y - 1

          elif cell.trackType == TrackCellType.SWITCH_LEFT_DOWN:
            self.linedCells.append(cell)
            x = x - 1 
            if cell.getSwitchPosition() != 0:
              y = y + 1

          else:
            stillWalking = False  # Don't know where to go from here
            break

        else:  # Now walking right
          #print("Walking right")
          #print("Walking right - x=%d, y=%d, type=%s" % (x, y, cell.trackType))          
          if cell.trackType == TrackCellType.HORIZONTAL:
            self.linedCells.append(cell)
            x = x + 1
            
          elif cell.trackType == TrackCellType.END_HORIZ_RIGHT:
            self.linedCells.append(cell)
            if (x+1,y) in self.cellXY.keys():
              #print("Looking for next block at %d/%d" % (x-1, y))
              nextBlockCell = self.cellXY[(x+1,y)]
              nextBlock = nextBlockCell.owner.name
            else:
              pass
              #print("No next block at %d/%d" % (x-1, y))
            stillWalking = False # terminate walking

            
          elif cell.trackType == TrackCellType.END_HORIZ_LEFT:
            self.linedCells.append(cell)
            x = x + 1

          elif cell.trackType == TrackCellType.DIAG_LEFT_UP:
            self.linedCells.append(cell)
            x = x + 1
            y = y + 1

          elif cell.trackType == TrackCellType.DIAG_RIGHT_UP:
            self.linedCells.append(cell)
            x = x + 1
            y = y - 1

          elif cell.trackType == TrackCellType.ANGLE_LEFT_UP:
            self.linedCells.append(cell)
            x = x + 1

          elif cell.trackType == TrackCellType.ANGLE_LEFT_DOWN:
            self.linedCells.append(cell)
            x = x + 1

          elif cell.trackType == TrackCellType.ANGLE_RIGHT_UP:
            self.linedCells.append(cell)
            x = x + 1
            y = y - 1

          elif cell.trackType == TrackCellType.ANGLE_RIGHT_DOWN:
            self.linedCells.append(cell)
            x = x + 1
            y = y + 1

          elif cell.trackType == TrackCellType.SWITCH_RIGHT_UP:
            self.linedCells.append(cell)
            x = x + 1 
            if cell.switchState != 0:
              y = y - 1
          elif cell.trackType == TrackCellType.SWITCH_RIGHT_DOWN:
            self.linedCells.append(cell)
            x = x + 1 
            if cell.switchState != 0:
              y = y + 1

          elif cell.trackType == TrackCellType.SWITCH_LEFT_UP:
            self.linedCells.append(cell)
            x = x + 1 
          elif cell.trackType == TrackCellType.SWITCH_LEFT_DOWN:
            self.linedCells.append(cell)
            x = x + 1 
          else:
            stillWalking = False  # Don't know where to go from here
            break        
    except Exception as e:
      print(e)

    return nextBlock

  def getCells(self):
    return self.cells
    
