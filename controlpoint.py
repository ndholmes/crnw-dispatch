from cells import SignalCell,TrackCellColors,TrackCellType
from mrbusUtils import MRBusBit,MRBusPacket
import datetime

class ControlPoint:
  def __init__(self, config, txCallback, getItemCallback):
    self.name = config['name']
    self.lined = "none"
    self.signals = { }
    self.switches = { }
    self.routeCmds = { }
    self.routeClrCmds = { }
    self.blocks = { }
    self.sensors = { }
    self.txCallback = txCallback
    self.timelock = datetime.datetime.utcnow()
    self.getItemCallback = getItemCallback
    self.timeoutSeconds = 20
    
    if 'timeoutSeconds' in config.keys():
      self.timeoutSeconds = int(str(config['timeoutSeconds']), 0)
    
    
    for entranceSignal in config['entranceSignals']:
      self.signals[entranceSignal['role']] = getItemCallback('signal', entranceSignal['name'])
      if None == self.signals[entranceSignal['role']]:
        print("Error, can't find signal named [%s]" % (entranceSignal['name']))
      else:
        #print("Associating CP [%s] with signal [%s]" % (self.name, self.signals[entranceSignal['role']].name))
        self.signals[entranceSignal['role']].assocControlPoint(self)
        cmdBytes = entranceSignal['cmd'].split(',')
        self.routeCmds[entranceSignal['role']] = MRBusPacket(cmdBytes[0], 0xFE, cmdBytes[1], [int(str(d),0) for d in cmdBytes[2:]])

        cmdBytes = entranceSignal['clr_cmd'].split(',')
        self.routeClrCmds[entranceSignal['role']] = MRBusPacket(cmdBytes[0], 0xFE, cmdBytes[1], [int(str(d),0) for d in cmdBytes[2:]])

    for switchConfig in config['switches']:
      self.switches[switchConfig['role']] = getItemCallback('switch', switchConfig['name'])
      if None == self.switches[switchConfig['role']]:
        print("Error, can't find switch named [%s]" % (switchConfig['name']))
      else:
        #print("Associating CP [%s] with switch [%s]" % (self.name, self.switches[switchConfig['role']].name))
        self.switches[switchConfig['role']].assocControlPoint(self)

    for blockConfig in config['blocks']:
      self.blocks[blockConfig['role']] = getItemCallback('block', blockConfig['name'])
      if None == self.blocks[blockConfig['role']]:
        print("Error, can't find block named [%s]" % (blockConfig['name']))
      else:
        #print("Associating CP [%s] with block [%s]" % (self.name, self.blocks[blockConfig['role']].name))
        self.blocks[blockConfig['role']].assocControlPoint(self)

    for sensorConfig in config['sensors']:
      self.sensors[sensorConfig['role']] = MRBusBit(sensorConfig['source'])




  def removeRoute(self, entranceSignal):
    print("Signal [%s] has asked to unline CP [%s]" % (entranceSignal, self.name))    

    if self.lined == "none":
      return False  # Already no route lined, can't clear one

    reqSignalRole = None
    
    for role in self.signals.keys():
      signal = self.signals[role]
      if (signal.name == entranceSignal):
        reqSignalRole = role
        break

    if reqSignalRole == None:  # Can't figure out what signal asked us for something
      return False

    if not self.signals[reqSignalRole].lined: # if the signal isn't lined, can't unline it
      return False

    osOccupied = False
    for blockName in self.blocks.keys():
      block = self.blocks[blockName]
      if block.isOccupied() or block.isManual():
        osOccupied = True
        break

    if osOccupied:  # Permission to unline route denied, OS is occupied
      return False
      
    self.lined = "run_time"
    self.timelock = datetime.datetime.utcnow()
    self.txCallback(self.routeClrCmds[reqSignalRole])


  # This is probably the function that gets overridden in the case of other than siding ends
  def lineRoute(self, entranceSignal):
    reqSignalRole = None
    
    for role in self.signals.keys():
      signal = self.signals[role]
      if (signal.name == entranceSignal):
        reqSignalRole = role
        break

    if reqSignalRole == None:  # Can't figure out what signal asked us for something
      return False

    print("Signal [%s] has asked to line CP [%s]" % (entranceSignal, self.name))    

    if self.lined != "none":
      return False  # Already lined, can't line another route

    osOccupied = False
    for blockName in self.blocks.keys():
      block = self.blocks[blockName]
      if block.isOccupied() or block.isManual():
        osOccupied = True
        break

    if osOccupied:  # Permission to line route denied, OS is occupied
      return False

    if self.switches['main'].positionReverse and reqSignalRole == 'main':
      return False # Points lined against main
      
    if self.switches['main'].positionNormal and reqSignalRole == 'siding':
      return False # Points lined against siding

    # Okay, things look fine, let's go ahead and line things
    self.txCallback(self.routeCmds[reqSignalRole])
    return True

  def processPacket(self, pkt):
    changed = False

    if self.lined == "run_time":
      if (datetime.datetime.utcnow() - self.timelock).total_seconds() >= self.timeoutSeconds:
        self.lined = "none"
        print("Timelock on [%s] expired" % (self.name))
        changed = True

    for sensorName in self.sensors.keys():
      changed = self.sensors[sensorName].testPacket(pkt) or changed

    for sensorName in self.sensors.keys():
      changed = self.sensors[sensorName].packetApplies(pkt) or changed


    if changed:
      self.recalculateState()
      
  def clearRouteTrace(self):
    nextBlockName = self.blocks['main'].clearRoute()
    while (None != nextBlockName and "" != nextBlockName):
      nextBlock = self.getItemCallback('block', nextBlockName)
      #print("Next block is %s" % (nextBlock.name))
      if None == nextBlock or nextBlock.cp == True:
        break
      nextBlockName = nextBlock.clearRoute()

  def setRouteTrace(self, leftBound, x, y):
    nextBlockName = self.blocks['main'].setRoute(leftBound, x, y)
    while (None != nextBlockName):
      nextBlock = self.getItemCallback('block', nextBlockName)
      #print("Next block left is %s" % (nextBlock.name))
      if None == nextBlock or nextBlock.cp == True:
        break
      nextBlockName = nextBlock.setRoute(leftBound)

  def recalculateState(self):
    try:
      self.recalculateStateReal()
    except Exception as e:
      print(e)

  def recalculateStateReal(self):
    print("Starting recalculateState for [%s]" % (self.name))
    
    if self.lined == "run_time":
      self.signals['points'].setIndication(False, False, True)
      self.signals['main'].setIndication(False, False, True)
      self.signals['siding'].setIndication(False, False, True)
      self.clearRouteTrace()
      
    elif self.sensors['sensorLinedLeft'].getState():
      #print("Sensor is lined left/south/east")
      self.lined = "left"
    
      #if self.signals['points'].leftBound:
      #  print("Points is leftbound")
      #else:
      #  print("Points is rightbound")
      
      self.switches['main'].setLock()
      if self.signals['points'].leftBound:  # doesn't matter how points are set
        (x,y) = self.signals['points'].getTrackXY()
        self.signals['points'].setIndication(True, False)
        self.signals['main'].setIndication(False, False)
        self.signals['siding'].setIndication(False, False)

      elif self.switches['main'].positionNormal:
        (x,y) = self.signals['main'].getTrackXY()
        self.signals['points'].setIndication(False, False)
        self.signals['main'].setIndication(True, False)
        self.signals['siding'].setIndication(False, False)

      elif self.switches['main'].positionReverse:
        (x,y) = self.signals['siding'].getTrackXY()
        self.signals['points'].setIndication(False, False)
        self.signals['main'].setIndication(False, False)
        self.signals['siding'].setIndication(True, False)

      self.setRouteTrace(True, x, y)

    elif self.sensors['sensorLinedRight'].getState():
      #print("Sensor is lined right/north/west")
      self.lined = "right"
      self.switches['main'].setLock()

      if not self.signals['points'].leftBound:  # doesn't matter how points are set
        (x,y) = self.signals['points'].getTrackXY()
        self.signals['points'].setIndication(True, False)
        self.signals['main'].setIndication(False, False)
        self.signals['siding'].setIndication(False, False)

      elif self.switches['main'].positionNormal:
        (x,y) = self.signals['main'].getTrackXY()
        self.signals['points'].setIndication(False, False)
        self.signals['main'].setIndication(True, False)
        self.signals['siding'].setIndication(False, False)

      elif self.switches['main'].positionReverse:
        (x,y) = self.signals['siding'].getTrackXY()
        self.signals['points'].setIndication(False, False)
        self.signals['main'].setIndication(False, False)
        self.signals['siding'].setIndication(True, False)
        
      self.setRouteTrace(False, x, y)

    else:
      self.lined = "none"
      #print("No lined route on [%s]" % (self.name))
      self.switches['main'].clearLock()
      self.signals['points'].setIndication(False, False)
      self.signals['main'].setIndication(False, False)
      self.signals['siding'].setIndication(False, False)
      self.clearRouteTrace()


    for signal in self.signals.values():
      signal.recalculateState()
      
    for switch in self.switches.values():
      switch.recalculateState()

    print("Ending recalculateState for [%s]" % (self.name))
