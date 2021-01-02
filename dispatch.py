#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Start of CR&NW Dispatching Panel

Basic theory:
 - Load pile of tiles from conf file
 - Draw on screen, load up in array of objects
 - Each object has various attributes
    - Screen x,y
    - Tile type
    - Block
    - LC handler
    - RC handler

   - Block Properties
    - Name
    - Left End
    - Right End
    - OS Point Name
    - IsConnector

   - Signal Properties
    - Name

   - Switch Properties
    - Name
    - Normal Left Block
    - Normal Right Block
    - Reverse Left Block
    - Reverse Right Block


 - When packets come in, come into a background thread
   - Maps packet input to events
   - Events get handled by gui

 - When clicks comes in, localize to tile block
   - Normal track does nothing
   - Turnouts 






"""
import sys
import wx
import wx.adv
import re
import json
import paho.mqtt.client as mqtt
import queue
import socket
from cells import TrackCell, SignalCell, SwitchCell, TextCell, TrackCellType
from mrbusUtils import MRBusBit, MRBusPacket
from switch import Switch
from block import Block
from signal import Signal
from controlpoint import ControlPoint
from controlpoint_cp3 import ControlPoint_CP3
import datetime


# This class is used to pass packets between the mrbus/mqtt thread and the master gui thread
class MqttMRBus:
  incomingPkts = queue.Queue(maxsize=500)
  def __init__(self):
    pass


class DispatchConsole(wx.Frame):
  cells = []
  blocks = [ ]
  signals = []
  switches = []
  controlpoints = []
  clickables = { }
  cellXY = { }
  menuHeight = 0
  currentBlockType = 0
  gridOn = False
  layoutData = None
  pktTimer = None
  terminate = False
  timerCnt = 0
  blinkCnt = 0
  blinkState = False
  fcAddress = 0
  secondTicker = 0
  pktsLastSecond = 0
  
  def __init__(self, railroadLayoutData, mqttMRBus, mqttClient):
    super().__init__(None)
    self.layoutData = railroadLayoutData
    self.InitUI()
    self.mqttClient = mqttClient
    self.mqttMRBus = mqttMRBus

    self.pktTimer = wx.Timer(self, 1)
    self.Bind(wx.EVT_TIMER, self.OnTimer)
    self.pktTimer.Start(100)
    print(wx.version())

  def txPacket(self, pkt):
    message = pkt.toJSON()
    topic = 'crnw/send'
    print("Sending [%s]  [%s]" % (topic, message))
    self.mqttClient.publish(topic=topic, payload=message)
    print("Sent")
    
  def doDisplayUpdate(self):
    dc = wx.ClientDC(self)
    # Since the cells all know if they changed since last time,
    # just loop through them and call draw on the ones that changed
    for i in self.cells:
      if i.needsRedraw():
        i.draw(dc)

  def applyPacket(self, pkt):
    for i in range(0, len(self.blocks)):
      self.blocks[i].processPacket(pkt)
        
    for i in range(0, len(self.switches)):
      self.switches[i].processPacket(pkt)

    for i in range(0, len(self.signals)):
      self.signals[i].processPacket(pkt)

    for i in range(0, len(self.controlpoints)):
      self.controlpoints[i].processPacket(pkt)

    if 0 != self.fcAddress and pkt.src == self.fcAddress:
      self.fastClockUpdate(pkt)

    self.doDisplayUpdate()

  def updateBlinkyCells(self, blinkState):
    blinkiesExist = False
    for signal in self.signals:
      if signal.cell.isBlinky():
        blinkiesExist = True
        signal.cell.setBlinkState(blinkState)
    return blinkiesExist

  def fastClockUpdate(self, pkt):
    try:
      self.realFastClockUpdate(pkt)
    except Exception as e:
      print(e)
      
  
  def realFastClockUpdate(self, pkt):
    print("Doing FC Update")
    if pkt.src != self.fcAddress or pkt.cmd != ord('T') or len(pkt.data) < 12:
      return
    
    flags = pkt.data[3]
    try:
      fastTime = datetime.time(pkt.data[4], pkt.data[5], pkt.data[6])
    except Exception as e:
      print(e)
      fastTime = None

    fastHold = False
    if (flags & 0x02) != 0:
      fastHold = True

    fastFactor = pkt.data[7] * 256 + pkt.data[8]
    inFastMode = flags & 0x01
    displayRealAMPM = False;
    if (flags & 0x04) != 0:
      displayRealAMPM = True
    
    displayFastAMPM = False;
    if (flags & 0x08) != 0:
      displayFastAMPM = True
    try:
      year = (pkt.data[9] * 16) + ((pkt.data[10]<<4) & 0xF0)
      month = pkt.data[10] & 0x0F
      day = pkt.data[11]
      realTime = datetime.datetime(year, month, day, pkt.data[0], pkt.data[1], pkt.data[2])
    except Exception as e:
      print(e)
      realTime = None
    fastTimeStr = ""
    if None != fastTime:
      if fastHold:
        fastTimeStr = fastTime.strftime("FAST: HOLD")
      elif displayFastAMPM:
        fastTimeStr = fastTime.strftime("FAST: %I:%M:%S%p")
      else:
        fastTimeStr = fastTime.strftime("FAST: %H:%M:%S")

    if None != realTime:
      fastTimeStr += "   "
      if displayRealAMPM:
        fastTimeStr += realTime.strftime("REAL: %I:%M:%S%p")
      else:
        fastTimeStr += realTime.strftime("REAL: %H:%M:%S")


    self.SetStatusText(fastTimeStr)
  
  def panelToPNG(self):
    #Create a DC for the whole screen area
    dcScreen = wx.ClientDC(self)
    w,h = dcScreen.GetSize()
    #Create a Bitmap that will later on hold the screenshot image
    #Note that the Bitmap must have a size big enough to hold the screenshot
    #-1 means using the current default colour depth
    bmp = wx.Bitmap(w,h)

    #Create a memory DC that will be used for actually taking the screenshot
    memDC = wx.MemoryDC()

    #Tell the memory DC to use our Bitmap
    #all drawing action on the memory DC will go to the Bitmap now
    memDC.SelectObject(bmp)

    #Blit (in this case copy) the actual screen on the memory DC
    #and thus the Bitmap
    memDC.Blit( 0, #Copy to this X coordinate
      0, #Copy to this Y coordinate
      w,h,
      dcScreen, #From where do we copy?
      0, 0
    )

    #Select the Bitmap out of the memory DC by selecting a new
    #uninitialized Bitmap
    memDC.SelectObject(wx.NullBitmap)
    img = bmp.ConvertToImage()
    fileName = "myImage.png"
    img.SaveFile(fileName, wx.BITMAP_TYPE_PNG) 
  
  def OnTimer(self, event):
    self.timerCnt += 1
    self.blinkCnt += 1
    self.secondTicker += 1
    
    if self.blinkCnt > 5:
      self.blinkCnt = 0
      self.blinkState = not self.blinkState
      blinkiesExist = self.updateBlinkyCells(self.blinkState)
      if blinkiesExist:  # don't do all the display update stuff if there are no blinking elements
        self.doDisplayUpdate()

    if self.secondTicker >= 10:
      self.SetStatusText("PPS: %d" % self.pktsLastSecond, 2)
      self.secondTicker = 0
      self.pktsLastSecond = 0
      #self.panelToPNG()
    
    while not self.mqttMRBus.incomingPkts.empty():
      try:
        pkt = self.mqttMRBus.incomingPkts.get_nowait()
        self.pktsLastSecond += 1
        #print("pkt: %s" % (pkt))
        self.applyPacket(pkt)
      except:
        pass

    if self.terminate:
      self.close()

  def isSignalCell(self, cellType):
    if cellType in ['signal_left', 'signal_right']:
      return True
    return False
    
  def isSwitchCell(self, cellType):
    if cellType in ['switch_left_up', 'switch_left_down', 'switch_right_up', 'switch_right_down']:
      return True
    return False
    
  def isTrackCell(self, cellType):
    if cellType in ['switch_left_up', 'switch_left_down', 'switch_right_up', 'switch_right_down']:
      return True
    return False

  def getRailroadObject(self, objectType, objectName):
    objectList = {'switch':self.switches, 'signal':self.signals, 'block':self.blocks}
    
    if objectType not in objectList.keys():
      return None
    
    for i in range(0, len(objectList[objectType])):
      if objectList[objectType][i].name == objectName:
        return objectList[objectType][i]

    return None
    
  def InitUI(self):
    self.Bind(wx.EVT_PAINT, self.OnPaint)
    self.Bind(wx.EVT_SIZE, self.OnPaint)
    self.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
    
    titleName = "MRBus Dispatch Console"
    if 'layoutName' in self.layoutData:
      titleName = self.layoutData['layoutName']
    
    self.SetTitle(titleName)
    self.SetSize((1200,900))
    self.Centre()
    self.Show(True)
    # create a menu bar
    self.makeMenuBar()

    if "gridOn" in self.layoutData.keys():
      if 1 == self.layoutData['gridOn']:
        self.gridOn = True
    
    if "fastClockAddress" in self.layoutData.keys():
      self.fcAddress = int(str(self.layoutData['fastClockAddress']), 0)
        
    
    
    
    for text in self.layoutData['text']:
      newCell = TextCell()
      newCell.setText(text['value'])
      x = int(text['x'])
      y = int(text['y'])
      newCell.setXY(x, y)
      if text['type'] == 'blockname':
        newCell.setColor('#ccffff')
      self.cells.append(newCell)

    for signalconfig in self.layoutData['signals']:
      newSignal = Signal(signalconfig, self.txPacket)
      self.signals.append(newSignal)
      self.cells = self.cells + newSignal.getCells()
      self.clickables[newSignal.getClickXY()] = newSignal.onLeftClick

    for switchconfig in self.layoutData['switches']:
      newSwitch = Switch(switchconfig, self.txPacket)
      self.switches.append(newSwitch)
      self.cells = self.cells + newSwitch.getCells()
      self.clickables[newSwitch.getClickXY()] = newSwitch.onLeftClick

    for blockconfig in self.layoutData['blocks']:
      newBlock = Block(blockconfig, self.txPacket, self.cellXY)
      self.blocks.append(newBlock)
      self.cells = self.cells + newBlock.getCells()

    for cell in self.cells:
      # Build a cell finder
      self.cellXY[(cell.cell_x,cell.cell_y)] = cell

    for cpconfig in self.layoutData['controlPoints']:
      if cpconfig['type'] == 'cp3':
        newCP = ControlPoint_CP3(cpconfig, self.txPacket, self.getRailroadObject)
      else:
        newCP = ControlPoint(cpconfig, self.txPacket, self.getRailroadObject)
      self.controlpoints.append(newCP)

    # and a status bar in a pear tree! :)
    self.statusbar = self.CreateStatusBar(3)
    self.statusbar.SetStatusWidths([-1,-1,200])
    self.statusbar.SetStatusText("Field 1")
    self.statusbar.SetStatusText("Field 2", 1)
    self.statusbar.SetStatusText("Field 3", 2)


  def OnLeftDown(self, e):
    x,y = e.GetPosition()
    block_x = x//16
    block_y = y//16

    ctrlState = wx.GetKeyState(wx.WXK_CONTROL)
    
    m = (block_x, block_y)
    if m in self.clickables:
      self.clickables[m](ctrl=ctrlState)
  
#      dc = wx.PaintDC(self)
#      self.cells[0].setSwitchPosition([1,0][self.cells[0].getSwitchPosition()])
#      self.cells[0].draw(wx.PaintDC(self))

  def OnPaint(self, e):
    dc = wx.ClientDC(self)
    (size_x, size_y) = self.GetSize()
    dc.SetBackground(wx.Brush('#000'))
    dc.Clear()

    dc.SetBrush(wx.Brush('#000'))
    if self.gridOn:
      dc.SetPen(wx.Pen("#AAA", width=1))
      for x in range(0, size_x//16):
        for y in range(0, size_y//16):
          dc.DrawRectangle(x*16, y*16, 17, 17)

    dc.SetPen(wx.Pen("#FFF", width=2))

    for cell in self.cells:
      cell.draw(dc)





  def makeMenuBar(self):
    """
    A menu bar is composed of menus, which are composed of menu items.
    This method builds a set of menus and binds handlers to be called
    when the menu item is selected.
    """

    # Make a file menu with Hello and Exit items
    fileMenu = wx.Menu()
    # The "\t..." syntax defines an accelerator key that also triggers
    # the same event
    helloItem = fileMenu.Append(-1, "&Hello...\tCtrl-H",
      "Help string shown in status bar for this menu item")
    fileMenu.AppendSeparator()
    # When using a stock ID we don't need to specify the menu item's
    # label
    exitItem = fileMenu.Append(wx.ID_EXIT)

    # Now a help menu for the about item
    helpMenu = wx.Menu()
    aboutItem = helpMenu.Append(wx.ID_ABOUT)

    # Make the menu bar and add the two menus to it. The '&' defines
    # that the next letter is the "mnemonic" for the menu item. On the
    # platforms that support it those letters are underlined and can be
    # triggered from the keyboard.
    menuBar = wx.MenuBar()
    menuBar.Append(fileMenu, "&File")
    menuBar.Append(helpMenu, "&Help")

    # Give the menu bar to the frame
    self.SetMenuBar(menuBar)

    # Finally, associate a handler function with the EVT_MENU event for
    # each of the menu items. That means that when that menu item is
    # activated then the associated handler function will be called.
    self.Bind(wx.EVT_MENU, self.OnHello, helloItem)
    self.Bind(wx.EVT_MENU, self.OnExit,  exitItem)
    self.Bind(wx.EVT_MENU, self.OnAbout, aboutItem)

  def OnExit(self, event):
    """Close the frame, terminating the application."""
    self.Close(True)


  def OnHello(self, event):
    """Say hello to the user."""
    wx.MessageBox("Hello again from wxPython")

  def OnAbout(self, event):
    """Display an About Dialog"""
    wx.MessageBox("This is a wxPython Hello World sample",
      "About Hello World 2",
      wx.OK|wx.ICON_INFORMATION)


def mqtt_onMessage(client, userdata, message):
  contents = message.payload.decode()
  mqttMRBus = userdata['mrbus']
  pkt = MRBusPacket.fromJSON(contents)
  if pkt is not None:
    mqttMRBus.incomingPkts.put(pkt)
    #print("Adding pkt %s" % (pkt))
  else:
    print("Packet failed")

def mqtt_onConnect(client, userdata, flags, rc):
#  logger = userdata['logger']
  print("In mqtt_onConnect")
  if rc == 0:
    # Successful Connection
    #logger.info("Successful MQTT Connection")
    print("Successful MQTT Connection")
    client.connected_flag = True
  elif rc == 1:
    print("ERROR: MQTT Incorrect Protocol Version")
    client.connected_flag = False
  elif rc == 2:
    print("ERROR: MQTT Invalid Client ID")
    client.connected_flag = False
  elif rc == 3:
    print("ERROR: MQTT Broker Unavailable")
    client.connected_flag = False
  elif rc == 4:
    print("ERROR: MQTT Bad Username/Password")
    client.connected_flag = False
  elif rc == 5:
    print("ERROR: MQTT Not Authorized")
    client.connected_flag = False
  else:
    print("ERROR: MQTT Other Failure %d" % (rc))
    client.connected_flag = False

def main():
  
  mqttMRBus = MqttMRBus()
  try:
    with open('layout.json') as f:
      layoutData = json.load(f)
  except Exception as e:
    print(e)
    print("Cannot load layout.json configuration file")
    sys.exit(-1)

  udata = { 'mrbus':mqttMRBus }
  clientName = socket.getfqdn()
  mqttClient = mqtt.Client(clientName, userdata=udata)
  mqttClient.on_message=mqtt_onMessage
  mqttClient.on_connect=mqtt_onConnect
  
  mqttHost = "crnw.drgw.net"
  mqttPort = 1883
  
  if 'mqttHost' in layoutData.keys():
    mqttHost = layoutData['mqttHost']
  if 'mqttPort' in layoutData.keys():
    mqttPort = int(layoutData['mqttPort'])
  
  mqttClient.connect(mqttHost, mqttPort, 60)
  mqttClient.loop_start()
  mqttClient.subscribe("crnw/raw")

  app = wx.App()
  ex = DispatchConsole(layoutData, mqttMRBus, mqttClient)
  ex.Show()
  app.MainLoop()


if __name__ == '__main__':
  main()

