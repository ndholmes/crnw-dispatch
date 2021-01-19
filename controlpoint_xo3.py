from cells import SignalCell,TrackCellColors,TrackCellType
from mrbusUtils import MRBusBit,MRBusPacket
import datetime

class ControlPoint_XO3:
  def __init__(self, config, txCallback, getItemCallback):
    self.name = config['name']
    self.lined = { 'main_1':'none', 'main_2':'none' }
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
    self.type = "Unknown"
    self.debug = False
    
    if 'timeoutSeconds' in config.keys():
      self.timeoutSeconds = int(str(config['timeoutSeconds']), 0)
    
    if 'debug' in config.keys() and int(config['debug']) == 1:
      self.debug = True
    
    self.type = config['type']
    
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

        self.sensors[entranceSignal['role']] = MRBusBit(entranceSignal['sensor'])

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

    if 'sensors' in config.keys():
      for sensorConfig in config['sensors']:
        self.sensors[sensorConfig['role']] = MRBusBit(sensorConfig['source'])

  def removeRoute(self, entranceSignal):
    print("Signal [%s] has asked to unline CP [%s]" % (entranceSignal, self.name))    

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

    if self.switches['switch_e_xover_1'].positionReverse or self.switches['switch_e_xover_2'].positionReverse \
      or self.switches['switch_w_xover_1'].positionReverse or self.switches['switch_w_xover_2'].positionReverse:
      self.lined['main_1'] = 'run_time'
      self.lined['main_2'] = 'run_time'
    elif reqSignalRole in [ 'main_1_w', 'main_1_e', 'main_3_w' ]:
      self.lined['main_1'] = 'run_time'
    elif reqSignalRole in [ 'main_2_w', 'main_2_e' ]:
      self.lined['main_2'] = 'run_time'
      
    self.timelock = datetime.datetime.utcnow()
    self.txCallback(self.routeClrCmds[reqSignalRole])
    return True  # Successfully unlined

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

    # Check if this signal would need a main that's already lined
    alreadyLined = False
    if self.switches['switch_e_xover_1'].positionReverse or self.switches['switch_e_xover_2'].positionReverse \
      or self.switches['switch_w_xover_1'].positionReverse or self.switches['switch_w_xover_2'].positionReverse:

      if self.lined['main_1'] != 'none' or self.lined['main_2'] != 'none':
        alreadyLined = True
    elif reqSignalRole in [ 'main_3_w', 'main_1_w', 'main_1_e' ]:
      if self.lined['main_1'] != 'none':
        alreadyLined = True
    elif reqSignalRole in [ 'main_2_w', 'main_2_e' ]:
      if self.lined['main_2'] != 'none':
        alreadyLined = True

    if alreadyLined:
      print("Cannot line route, already lined through CP")
      return False

    print("CP [%s] Checkpoint 2" % (self.name))


    # Check if the mainlines needed are already occupied
    osOccupied = False
    osManual = False
    
    if self.switches['switch_e_xover_1'].positionReverse or self.switches['switch_e_xover_2'].positionReverse or self.switches['switch_w_xover_1'].positionReverse or self.switches['switch_w_xover_2'].positionReverse:
      osOccupied = self.blocks['main_1'].isOccupied() or self.blocks['main_2'].isOccupied()
      osManual = self.blocks['main_1'].isManual() or self.blocks['main_2'].isManual()
    elif reqSignalRole in [ 'main_1_w', 'main_1_e' ]:
      osOccupied = self.blocks['main_1'].isOccupied()
      osManual = self.blocks['main_1'].isManual()
    elif reqSignalRole in [ 'main_2_w', 'main_2_e' ]:
      osOccupied = self.blocks['main_2'].isOccupied()
      osManual = self.blocks['main_2'].isManual()

    if osOccupied or osManual:  # Permission to line route denied, OS is occupied or in manual mode
      return False
    
    print("CP [%s] sigrole [%s] e_xover=%s/%s  w_xover=%s/%s m1_m3=%s/%s" % (self.name, reqSignalRole, self.switches['switch_e_xover_1'].positionNormal, self.switches['switch_e_xover_1'].positionReverse, self.switches['switch_w_xover_1'].positionNormal, self.switches['switch_w_xover_1'].positionReverse, self.switches['switch_m1_m3'].positionNormal, self.switches['switch_m1_m3'].positionReverse))

# West/North                          East/South
#                   W-XOVER   E-XOVER
#                      |         |
#      M2W-> |-O       v         v
#    M2 ------------------------------  M2
#      M1W-> |-O       \        /  O-| <-M2E
#    M1 ------------------------------  M1
#      M3W-> |-O   /  <- M1_M3
#    M3 -----------

    # Test to see if any conflicting routes are already lined
    
    if reqSignalRole == 'main_1_e' and self.switches['switch_e_xover_1'].positionReverse:
      return False  # Points lined against main 1 westbound

    if reqSignalRole == 'main_2_e' and self.switches['switch_w_xover_2'].positionReverse and not self.switches['switch_e_xover_2'].positionReverse:
      return False  # Points lined against main 2 westbound

    if reqSignalRole == 'main_2_e' and self.switches['switch_e_xover_2'].positionNormal and self.switches['switch_w_xover_2'].positionReverse:
      return False  # Points lined against main 2 westbound

    if reqSignalRole == 'main_1_w' and (self.switches['switch_w_xover_2'].positionReverse or self.switches['switch_m1_m3'].positionReverse):
      return False  # Points lined against main 1 eastbound

    if reqSignalRole == 'main_3_w' and (self.switches['switch_w_xover_2'].positionReverse or self.switches['switch_m1_m3'].positionNormal):
      return False  # Points lined against main 3 eastbound

    if reqSignalRole == 'main_2_w' and self.switches['switch_e_xover_2'].positionReverse and not self.switches['switch_w_xover_2'].positionReverse:
      return False  # Points lined against main 2 eastbound

    print("Sending lining command")

    # Okay, things look fine, let's go ahead and line things
    self.txCallback(self.routeCmds[reqSignalRole])
    return True

  def processPacket(self, pkt):
    changed = False

    if self.lined['main_1'] == "run_time":
      if (datetime.datetime.utcnow() - self.timelock).total_seconds() >= self.timeoutSeconds:
        self.lined['main_1'] = "none"
        print("Timelock on [%s] expired" % (self.name))
        changed = True

    if self.lined['main_2'] == "run_time":
      if (datetime.datetime.utcnow() - self.timelock).total_seconds() >= self.timeoutSeconds:
        self.lined['main_2'] = 'none'
        print("Timelock on [%s] expired" % (self.name))
        changed = True


    for sensorName in self.sensors.keys():
      changed = self.sensors[sensorName].testPacket(pkt) or changed

    for sensorName in self.sensors.keys():
      changed = self.sensors[sensorName].packetApplies(pkt) or changed

    if changed:
      self.recalculateState()
      
  def clearRouteTrace(self, whichBlock='main'):
    if self.debug:
      print("Clearing route [%s]" % (whichBlock))
    nextBlockName = self.blocks[whichBlock].clearRoute()
    
    while (None != nextBlockName and "" != nextBlockName):
      nextBlock = self.getItemCallback('block', nextBlockName)
      #print("Next block is %s" % (nextBlock.name))
      if None == nextBlock or nextBlock.cp == True:
        break
      nextBlockName = nextBlock.clearRoute()

  def setRouteTrace(self, whichBlock, leftBound, x, y):
    nextBlockName = self.blocks[whichBlock].setRoute(leftBound, x, y)
    while (None != nextBlockName):
      nextBlock = self.getItemCallback('block', nextBlockName)
      if None == nextBlock or nextBlock.cp == True:
        break
      nextBlockName = nextBlock.setRoute(leftBound)

  def lockAllSwitches(self):
    self.switches['switch_e_xover_1'].setLock()
    self.switches['switch_e_xover_2'].setLock()
    self.switches['switch_w_xover_1'].setLock()
    self.switches['switch_w_xover_2'].setLock()
    self.switches['switch_m1_m3'].setLock()

  def unlockAllSwitches(self):
    self.switches['switch_e_xover_1'].clearLock()
    self.switches['switch_e_xover_2'].clearLock()
    self.switches['switch_w_xover_1'].clearLock()
    self.switches['switch_w_xover_2'].clearLock()
    self.switches['switch_m1_m3'].clearLock()


  def recalculateState(self):
    try:
      self.recalculateStateReal()
    except Exception as e:
      print ("Exception in %s.recalculateStateReal()" % (self.name))
      print(e)

# West/North                          East/South
#                   W-XOVER   E-XOVER
#                      |         |
#      M2W-> |-O       v         v
#    M2 ------------------------------  M2
#      M1W-> |-O       \        /  O-| <-M2E
#    M1 ------------------------------  M1
#      M3W-> |-O   /  <- M1_M3     O-| <-M1E
#    M3 -----------



  def recalculateStateReal(self):
    if self.debug:
      print("Starting recalculateState for [%s]" % (self.name))
      print("Current state main1=[%s] main2=[%s]" % (self.lined['main_1'], self.lined['main_2']))

    
    if self.sensors['main_1_e'].getState():
      if self.debug:
        print("main_1_e is lined")

      (x,y) = self.signals['main_1_e'].getTrackXY()
      if self.switches['switch_e_xover_1'].positionNormal and self.switches['switch_e_xover_2'].positionNormal \
        and self.switches['switch_w_xover_1'].positionNormal and self.switches['switch_w_xover_2'].positionNormal \
        and self.switches['switch_m1_m3'].positionNormal:
        self.lockAllSwitches()
        self.signals['main_3_w'].setIndication(False, False)
        self.signals['main_1_w'].setIndication(False, False)
        self.signals['main_1_e'].setIndication(True, False)
        self.lined['main_1'] = 'right'
        self.setRouteTrace('main_1', False, x, y)
                
      elif self.switches['switch_e_xover_1'].positionReverse and self.switches['switch_e_xover_2'].positionReverse:
        self.lockAllSwitches()
        self.signals['main_1_w'].setIndication(False, False)
        self.signals['main_3_w'].setIndication(False, False)
        self.signals['main_1_e'].setIndication(True, False)
        self.signals['main_2_w'].setIndication(False, False)
        self.signals['main_2_e'].setIndication(False, False)
        self.lined['main_1'] = 'right'
        self.lined['main_2'] = 'right'
        self.setRouteTrace('main_1', False, x, y)
        self.setRouteTrace('main_2', False, x, y)
        
    elif self.sensors['main_1_w'].getState():
      if self.debug:
        print("main_1_w is lined")

      (x,y) = self.signals['main_1_w'].getTrackXY()
      if self.switches['switch_e_xover_1'].positionNormal and self.switches['switch_e_xover_2'].positionNormal \
        and self.switches['switch_w_xover_1'].positionNormal and self.switches['switch_w_xover_2'].positionNormal \
        and self.switches['switch_m1_m3'].positionNormal:

        self.lockAllSwitches()
        self.signals['main_1_e'].setIndication(False, False)
        self.signals['main_1_w'].setIndication(True, False)
        self.signals['main_3_w'].setIndication(False, False)
        self.lined['main_1'] = 'left'
        self.setRouteTrace('main_1', True, x, y)

      elif self.switches['switch_w_xover_1'].positionReverse and self.switches['switch_w_xover_2'].positionReverse and \
        ((self.switches['switch_e_xover_1'].positionNormal and self.switches['switch_e_xover_2'].positionNormal) \
          or (self.switches['switch_e_xover_1'].positionReverse and self.switches['switch_e_xover_2'].positionReverse)):

        self.lockAllSwitches()
        self.signals['main_1_e'].setIndication(False, False)
        self.signals['main_1_w'].setIndication(True, False)
        self.signals['main_2_e'].setIndication(False, False)
        self.signals['main_2_w'].setIndication(False, False)
        self.lined['main_1'] = 'left'
        self.lined['main_2'] = 'left'
        self.setRouteTrace('main_1', True, x, y)
        self.setRouteTrace('main_2', True, x, y)

    elif self.sensors['main_3_w'].getState():
      if self.debug:
        print("main_3_w is lined")

      (x,y) = self.signals['main_3_w'].getTrackXY()
      if self.switches['switch_m1_m3'].positionReverse and self.switches['switch_e_xover_1'].positionNormal \
        and self.switches['switch_e_xover_2'].positionNormal and self.switches['switch_w_xover_1'].positionNormal \
        and self.switches['switch_w_xover_2'].positionNormal:

        self.lockAllSwitches()
        self.signals['main_1_e'].setIndication(False, False)
        self.signals['main_1_w'].setIndication(False, False)
        self.signals['main_3_w'].setIndication(True, False)
        self.lined['main_1'] = 'left'
        
        self.setRouteTrace('main_1', True, x, y)

      elif self.switches['switch_m1_m3'].positionReverse and self.switches['switch_e_xover_1'].positionReverse \
        and self.switches['switch_e_xover_2'].positionReverse and self.switches['switch_w_xover_1'].positionNormal \
        and self.switches['switch_w_xover_2'].positionNormal:

        print("In m3w state 2")
        self.lockAllSwitches()
        self.signals['main_1_e'].setIndication(False, False)
        self.signals['main_1_w'].setIndication(False, False)
        self.signals['main_3_w'].setIndication(True, False)
        self.signals['main_2_e'].setIndication(False, False)
        self.signals['main_2_w'].setIndication(False, False)
        self.lined['main_1'] = 'left'
        self.lined['main_2'] = 'left'
        self.setRouteTrace('main_1', True, x, y)
        self.setRouteTrace('main_2', True, x, y)
        print("In m3w state 2 checkpoint end")

    elif self.lined['main_1'] == 'run_time':
      self.clearRouteTrace('main_1')
      self.signals['main_3_w'].setIndication(False, False, True)
      self.signals['main_1_w'].setIndication(False, False, True)
      self.signals['main_1_e'].setIndication(False, False, True)
    else:
      self.signals['main_3_w'].setIndication(False, False)
      self.signals['main_1_w'].setIndication(False, False)
      self.signals['main_1_e'].setIndication(False, False)
      if self.debug:
        print("main_1 is NOT lined")

      # If we're just lined for main two, then clear our route based on the fact no M2 signals are set
      if self.switches['switch_e_xover_1'].positionNormal and self.switches['switch_w_xover_1'].positionNormal:
        self.lined['main_1'] = 'none'
        self.clearRouteTrace('main_1')
      # If we're lined to main one via the XOVER
      elif (self.switches['switch_e_xover_1'].positionReverse or self.switches['switch_w_xover_1'].positionReverse) and not (self.sensors['main_2_w'].getState() or self.sensors['main_2_e'].getState()):
        self.lined['main_1'] = 'none'
        self.lined['main_2'] = 'none'
        self.clearRouteTrace('main_1')
        self.clearRouteTrace('main_2')

    if self.sensors['main_2_e'].getState():
      if self.debug:
        print("main_2_e is lined")

      (x,y) = self.signals['main_2_e'].getTrackXY()
      if self.switches['switch_e_xover_1'].positionNormal and self.switches['switch_e_xover_2'].positionNormal and self.switches['switch_w_xover_1'].positionNormal and self.switches['switch_w_xover_2'].positionNormal:
        self.lockAllSwitches()
        self.signals['main_2_w'].setIndication(False, False)
        self.signals['main_2_e'].setIndication(True, False)
        self.lined['main_2'] = 'right'
        self.setRouteTrace('main_2', False, x, y)
      elif self.switches['switch_e_xover_1'].positionReverse and self.switches['switch_e_xover_2'].positionReverse and self.switches['switch_w_xover_1'].positionReverse and self.switches['switch_w_xover_2'].positionReverse:
        self.lockAllSwitches()
        self.signals['main_2_w'].setIndication(False, False)
        self.signals['main_2_e'].setIndication(True, False)
        self.signals['main_1_w'].setIndication(False, False)
        self.signals['main_1_e'].setIndication(False, False)
        self.lined['main_1'] = 'right'
        self.lined['main_2'] = 'right'        
        self.setRouteTrace('main_1', False, x, y)
        self.setRouteTrace('main_2', False, x, y)
      elif self.switches['switch_e_xover_1'].positionReverse and self.switches['switch_e_xover_2'].positionReverse and self.switches['switch_w_xover_1'].positionNormal and self.switches['switch_w_xover_2'].positionNormal:
        self.lockAllSwitches()
        self.signals['main_2_w'].setIndication(False, False)
        self.signals['main_2_e'].setIndication(True, False)
        self.signals['main_1_w'].setIndication(False, False)
        self.signals['main_1_e'].setIndication(False, False)
        self.lined['main_1'] = 'right'
        self.lined['main_2'] = 'right'
        self.setRouteTrace('main_1', False, x, y)
        self.setRouteTrace('main_2', False, x, y)
        
    elif self.sensors['main_2_w'].getState():
      if self.debug:
        print("main_2_w is lined")

      (x,y) = self.signals['main_2_w'].getTrackXY()
      if self.switches['switch_e_xover_1'].positionNormal and self.switches['switch_e_xover_2'].positionNormal and self.switches['switch_w_xover_1'].positionNormal and self.switches['switch_w_xover_2'].positionNormal:
        self.lockAllSwitches()
        self.signals['main_2_w'].setIndication(True, False)
        self.signals['main_2_e'].setIndication(False, False)
        self.lined['main_2'] = 'left'
        self.setRouteTrace('main_2', True, x, y)
      elif self.switches['switch_e_xover_1'].positionReverse and self.switches['switch_e_xover_2'].positionReverse and self.switches['switch_w_xover_1'].positionReverse and self.switches['switch_w_xover_2'].positionReverse:
        self.lockAllSwitches()
        self.signals['main_2_w'].setIndication(True, False)
        self.signals['main_2_e'].setIndication(False, False)
        self.signals['main_1_w'].setIndication(False, False)
        self.signals['main_1_e'].setIndication(False, False)
        self.lined['main_1'] = 'left'
        self.lined['main_2'] = 'left'
        self.setRouteTrace('main_1', True, x, y)
        self.setRouteTrace('main_2', True, x, y)
      elif self.switches['switch_w_xover_1'].positionReverse and self.switches['switch_w_xover_2'].positionReverse and self.switches['switch_e_xover_1'].positionNormal and self.switches['switch_e_xover_2'].positionNormal:
        self.lockAllSwitches()
        self.signals['main_2_w'].setIndication(True, False)
        self.signals['main_2_e'].setIndication(False, False)
        self.signals['main_1_w'].setIndication(False, False)
        self.signals['main_1_e'].setIndication(False, False)
        self.lined['main_1'] = 'left'
        self.lined['main_2'] = 'left'
        self.setRouteTrace('main_1', True, x, y)
        self.setRouteTrace('main_2', True, x, y)
    elif self.lined['main_2'] == 'run_time':   
      self.clearRouteTrace('main_2')
      self.signals['main_2_w'].setIndication(False, False, True)
      self.signals['main_2_e'].setIndication(False, False, True)
    else:
      self.signals['main_2_w'].setIndication(False, False)
      self.signals['main_2_e'].setIndication(False, False)

      # If we're just lined for main two, then clear our route based on the fact no M2 signals are set
      if (self.switches['switch_e_xover_2'].positionNormal and self.switches['switch_w_xover_2'].positionNormal) or (self.switches['switch_e_xover_2'].positionReverse and self.switches['switch_w_xover_2'].positionReverse):
        self.lined['main_2'] = 'none'
        self.clearRouteTrace('main_2')
      # If we're lined to main one via the XOVER
      elif (self.switches['switch_e_xover_2'].positionReverse or self.switches['switch_w_xover_2'].positionReverse) and not (self.sensors['main_1_w'].getState() or self.sensors['main_3_w'].getState() or self.sensors['main_1_e'].getState()):
        self.lined['main_1'] = 'none'
        self.lined['main_2'] = 'none'
        self.clearRouteTrace('main_1')
        self.clearRouteTrace('main_2')

    if self.lined['main_1'] == 'none' and self.lined['main_2'] == 'none':
      self.unlockAllSwitches()


    for signal in self.signals.values():
      signal.recalculateState()
      
    for switch in self.switches.values():
      switch.recalculateState()

    if self.debug:
      print("Ending recalculateState for [%s]" % (self.name))
