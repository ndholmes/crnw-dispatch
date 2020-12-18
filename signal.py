from cells import SignalCell,TrackCellColors,TrackCellType
from mrbusUtils import MRBusBit,MRBusPacket

class Signal:
  def __init__(self, config, txCallback):
    self.name = config['name']
    self.lined = False
    self.unverified = True   # Set when a command has been issued but no response has come
    self.txCallback = txCallback

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

  # processPacket takes an incoming MRBus packet
  def processPacket(self, pkt):
    changed = self.sensorLined.testPacket(pkt)

    if changed:
      self.unverified = False
      self.lined = self.sensorLined.getState()
      self.recalculateState()

  def getClickXY(self):
    return (self.cell.getXY())

  def onLeftClick(self):
    print("Got click on signal [%s]" % self.name)
    if self.txCallback == None:
      return
    
    # Horrible hack
    newPos = 0x45

    ctrlpkt = {
      "S Eyak Points Signal" : MRBusPacket(0x38, 0xFE, 0x43, [0x01, 0x58, newPos]),
      "N Eyak Points Signal" : MRBusPacket(0x38, 0xFE, 0x43, [0x02, 0x58, newPos]),
      "S Alaganik Points Signal" : MRBusPacket(0x37, 0xFE, 0x43, [0x01, 0x58, newPos]),
      "N Alaganik Points Signal" : MRBusPacket(0x37, 0xFE, 0x43, [0x02, 0x58, newPos]),
    }

    pkt = ctrlpkt[self.name]

    print("Sending signal change pkt to %s\n[%s]" % (self.name, pkt))
    self.txCallback(pkt)
    self.unverified = True
    self.recalculateState()

  def recalculateState(self):
    print("Recalculating state for [%s]" % (self.name))
    
    defaultColor = TrackCellColors.getColor('signal_unknown')

    if self.unverified: 
      self.cell.setColor(TrackCellColors.getColor('signal_unknown'))
    elif self.lined:
      self.cell.setColor(TrackCellColors.getColor('signal_lined'))
    else:
      self.cell.setColor(TrackCellColors.getColor('signal_normal'))

  def getCells(self):
    return [self.cell]
    
