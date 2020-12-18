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
from cells import TrackCell, SignalCell, SwitchCell, TextCell, TrackCellType
from mrbusUtils import MRBusBit, MRBusPacket
from switch import Switch
from block import Block
from signal import Signal

import datetime


# This class is used to pass packets between the mrbus/mqtt thread and the master gui thread
class MqttMRBus:
  incomingPkts = queue.Queue(maxsize=500)
  def __init__(self):
    pass


class Example(wx.Frame):
  cells = []
  blocks = [ ]
  signals = []
  switches = []
  clickables = { }
  menuHeight = 0
  currentBlockType = 0
  gridOn = False
  layoutData = None
  pktTimer = None
  timerCnt = 0

  def __init__(self, railroadLayoutData, mqttMRBus, mqttClient):
    super(Example, self).__init__(None)
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
    for i in self.cells:
      if i.needsRedraw():
        i.draw(dc)

  def applyPacket(self, pkt):
    for i in range(0, len(self.blocks)):
      self.blocks[i].processPacket(pkt)
        
    for i in range(0, len(self.switches)):
      #print("Applying packet to %d - [%s]" % (i, self.switches[i].name))
      self.switches[i].processPacket(pkt)
      #print("Done")

    for i in range(0, len(self.signals)):
      self.signals[i].processPacket(pkt)


    self.doDisplayUpdate()

  def OnTimer(self, event):
    self.timerCnt += 1
#    ptstr = "LC at %u,%u - block %ux%u" % (x,y, block_x, block_y)
    #ptstr = "tmrcnt = %u pktcnt=%d" % (self.timerCnt, self.mqttMRBus.incomingPkts.qsize())

    while not self.mqttMRBus.incomingPkts.empty():
      try:
        pkt = self.mqttMRBus.incomingPkts.get_nowait()
        self.applyPacket(pkt)
      except:
        pass

    self.SetStatusText(ptstr)

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

  def InitUI(self):
    self.Bind(wx.EVT_PAINT, self.OnPaint)
    self.Bind(wx.EVT_SIZE, self.OnPaint)
    self.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
    self.SetTitle("CRNW Dispatch System")
    self.SetSize((1000,800))
    self.Centre()
    self.Show(True)
    # create a menu bar
    self.makeMenuBar()

    if "gridOn" in self.layoutData.keys():
      if 1 == self.layoutData['gridOn']:
        self.gridOn = True
    
    for text in self.layoutData['text']:
      newCell = TextCell()
      newCell.setText(text['value'])
      newCell.setXY(int(text['x']), int(text['y']))
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
      newBlock = Block(blockconfig, self.txPacket)
      self.blocks.append(newBlock)
      self.cells = self.cells + newBlock.getCells()
      
    # and a status bar in a pear tree! :)
    self.CreateStatusBar()
    self.SetStatusText("Welcome to wxPython!")


  def OnLeftDown(self, e):
    x,y = e.GetPosition()
    block_x = x//16
    block_y = y//16
    
    #ptstr = "LC at %u,%u - block %ux%u" % (x,y, block_x, block_y)
    #self.SetStatusText(ptstr)

    # Go figure out what we clicked - you can click turnouts and signals

    m = (block_x, block_y)
    if m in self.clickables:
      self.clickables[m]()
  
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
    print("Adding pkt %s" % (pkt))
  else:
    print("Packet failed")

def mqtt_onConnect(client, userdata, flags, rc):
#  logger = userdata['logger']
  print("I'M HERE!")
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
  mqttClient = mqtt.Client("Dispatch Console", userdata=udata)
  mqttClient.on_message=mqtt_onMessage
  mqttClient.on_connect=mqtt_onConnect
  mqttClient.connect("crnw.drgw.net", 1883, 60)
  mqttClient.loop_start()
  mqttClient.subscribe("crnw/raw")

  app = wx.App()
  ex = Example(layoutData, mqttMRBus, mqttClient)
  ex.Show()
  app.MainLoop()


if __name__ == '__main__':
  main()

