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
  def __init__(self, config, txCallback):
    self.name = config['name']
    self.manualControl = False
    self.occupied = False
    self.powerOn = True
    self.locked = False
    self.lined = False
    self.lastUpdated = datetime.datetime.now() - datetime.timedelta(days=30)  # just make this way in the past
    self.txCallback = txCallback
    self.base_x = 0
    self.base_y = 0
    
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

          newCell.setXY(cell_x, cell_y)
          if cell['type'] in cellType.keys():
            print("Placing cell of type [%s] at (%d,%d)" % (cell['type'], cell_x, cell_y))
            newCell.setType(cellType[cell['type']])
          else:
            print("Warnings - cell type %s not known at (%d,%d)" % (cell['type'], x, y))

          self.cells.append(newCell)

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

  def onLeftClick(self):
    return False  # Blocks don't respond to clicks

  def recalculateState(self):
    print("Recalculating state for [%s]" % (self.name))
    trackColor = TrackCellColors.getColor('track_unknown')

    # Compute track color
    if self.occupied:
      trackColor = TrackCellColors.getColor('track_occupied')
    elif self.lined:
      trackColor = TrackCellColors.getColor('track_lined')
    elif self.manualControl:
      trackColor = TrackCellColors.getColor('track_manual')
    else:
      trackColor = TrackCellColors.getColor('track_idle')

    for i in range(0, len(self.cells)):
      self.cells[i].setColor(trackColor)


  def getCells(self):
    return self.cells
    
