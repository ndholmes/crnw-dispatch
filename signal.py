from cells import SignalCell,TrackCellColors,TrackCellType
from mrbusUtils import MRBusBit,MRBusPacket

class Signal:
  def __init__(self, config, txCallback):
    self.name = config['name']
    self.lined = False
    self.unverified = True   # Set when a command has been issued but no response has come
    self.blinky = False
    self.txCallback = txCallback
    self.cp = None
    self.leftBound = False
    self.cell = SignalCell()
    self.cell.setXY(int(config['x']), int(config['y']))

    pattern = ""
    if "sensorLined" in config.keys():
      pattern = config['sensorLined']
    self.sensorLined = MRBusBit(pattern)

    cellType = {
      'signal_left':TrackCellType.SIG_SINGLE_LEFT,
      'signal_right':TrackCellType.SIG_SINGLE_RIGHT,
    }
    self.cell.setType(cellType[config['type']])
    if config['type'] == 'signal_left':
      self.leftBound = True
    else:
      self.leftBound = False


  # processPacket takes an incoming MRBus packet
  def processPacket(self, pkt):
    changed = self.sensorLined.testPacket(pkt)

    if self.unverified and self.sensorLined.packetApplies(pkt):
      changed = True

    if changed:
      self.unverified = False
      self.lined = self.sensorLined.getState()
      self.recalculateState()

  def getClickXY(self):
    return (self.cell.getXY())

  def assocControlPoint(self, controlPoint):
    self.cp = controlPoint
    print("Signal [%s] has associated with CP [%s]" % (self.name, self.cp.name))

  def setIndication(self, green, unverified=False, blinky=False):
    changed = False
    if self.lined != green:
      changed = True
      self.lined = green
    if self.unverified != unverified:
      changed = True
      self.unverified = unverified
    
    if self.blinky != blinky:
      changed = True
      self.blinky = blinky

    if changed:
      self.recalculateState()
    
  def getTrackXY(self):
    if self.cell.getType() == TrackCellType.SIG_SINGLE_LEFT:
      x = self.cell.cell_x
      y = self.cell.cell_y + 1
    else:
      x = self.cell.cell_x
      y = self.cell.cell_y - 1
    return (x,y)
    
  def onLeftClick(self, ctrl=False):
    print("Got click on signal [%s]" % self.name)
    result = False
    
    if self.cp != None:
      if ctrl:
        result = self.cp.removeRoute(self.name)
      else:
        result = self.cp.lineRoute(self.name)

    if result != False:
      self.unverified = True
      self.recalculateState()

  def recalculateState(self):
#    print("Recalculating state for [%s]" % (self.name))
    signalColor = TrackCellColors.getColor('signal_unknown')

    if self.unverified:
      signalColor = TrackCellColors.getColor('signal_unknown')
    elif self.lined:
      signalColor = TrackCellColors.getColor('signal_lined')
    else:
      signalColor = TrackCellColors.getColor('signal_normal')
    self.cell.setColor(signalColor, self.blinky)
#    print("Setting signal [%s] to %s" % (self.name, signalColor))


  def getCells(self):
    return [self.cell]
    
