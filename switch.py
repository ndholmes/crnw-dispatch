from cells import SwitchCell,TrackCellColors,TrackCellType
from mrbusUtils import MRBusBit

class Switch:
  def __init__(self, config, txCallback):
    self.name = config['name']
    
    self.positionNormal = True
    self.positionReverse = False
    self.manualControl = False
    self.occupied = False
    self.locked = False
    self.lined = False
    self.txCallback = txCallback
    
    pattern = ""
    if "sensorNormal" in config.keys():
      pattern = config['sensorNormal']
    self.sensorNormal = MRBusBit(pattern)
    
    pattern = ""
    if "sensorReverse" in config.keys():
      pattern = config['sensorReverse']
    self.sensorReverse = MRBusBit(pattern)

    pattern = ""
    if "sensorManual" in config.keys():
      pattern = config['sensorManual']
    self.sensorManual = MRBusBit(pattern)

    pattern = ""
    if "sensorOccupancy" in config.keys():
      pattern = config['sensorOccupancy']
    self.sensorOccupancy = MRBusBit(pattern)

    self.cell = SwitchCell()
    self.cell.setXY(int(config['x']), int(config['y']))
    cellType = {
      'switch_right_down':TrackCellType.SWITCH_RIGHT_DOWN,
      'switch_right_up':TrackCellType.SWITCH_RIGHT_UP,
      'switch_left_down':TrackCellType.SWITCH_LEFT_DOWN,
      'switch_left_up':TrackCellType.SWITCH_LEFT_UP,
    }
    self.cell.setType(cellType[config['type']])

  # processPacket takes an incoming MRBus packet
  def processPacket(self, pkt):
    changed = self.sensorNormal.testPacket(pkt)
    changed = self.sensorReverse.testPacket(pkt) or changed
    changed = self.sensorManual.testPacket(pkt) or changed
    changed = self.sensorOccupancy.testPacket(pkt) or changed

    if changed:
      self.positionNormal = self.sensorNormal.getState()
      self.positionReverse = self.sensorReverse.getState()
      self.manualControl = self.sensorManual.getState()
      self.occupied = self.sensorOccupancy.getState()
      self.recalculateState()
#    else:
#      print("Processed packet for [%s], no change in state" % (self.name))

  def onLeftClick(self):
    if self.occupied or self.locked or self.manualControl:
      return False

    # Change switch state to indeterminant
    self.positionNormal = False
    self.positionReverse = False


  def recalculateState(self):
    print("Recalculating state for [%s]" % (self.name))
    
    defaultColor = TrackCellColors.getColor('switch_unknown')
    # Compute switch square color
    if self.manualControl:  # Manual is first, since manual makes the OS "occupied"
      self.cell.setSwitchStatusColor(TrackCellColors.getColor('switch_manual'))
    elif self.locked or self.occupied:
      self.cell.setSwitchStatusColor(TrackCellColors.getColor('switch_locked'))
    elif self.positionNormal or self.positionReverse:
      self.cell.setSwitchStatusColor(TrackCellColors.getColor('switch_normal'))
    else:
      self.cell.setSwitchStatusColor(defaultColor)

    # Compute track color
    if self.lined:
      self.cell.setColor(TrackCellColors.getColor('track_lined'))
    elif self.occupied:
      self.cell.setColor(TrackCellColors.getColor('track_occupied'))
    else:
      self.cell.setColor(TrackCellColors.getColor('track_idle'))

    print("checkpoint 2")
    if self.positionNormal:
      self.cell.setSwitchPosition(0)
    elif self.positionReverse:
      self.cell.setSwitchPosition(1)
    # No else, if we don't know which position it's in, just leave it alone

  def getCells(self):
    return [self.cell]
    
