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
import json
import paho.mqtt.client as mqtt
import queue

from enum import Enum

class TrackBlockType(Enum):
  HORIZONTAL        = 1,
  DIAG_RIGHT_UP     = 2,
  DIAG_LEFT_UP      = 3,
  ANGLE_LEFT_DOWN   = 4,
  ANGLE_LEFT_UP     = 5,
  ANGLE_RIGHT_DOWN  = 6,
  ANGLE_RIGHT_UP    = 7,
  END_HORIZ_RIGHT   = 8,
  END_HORIZ_LEFT    = 9,
  
  SWITCH_RIGHT_UP   = 40,
  SWITCH_RIGHT_DOWN = 41,
  SWITCH_LEFT_UP    = 42,
  SWITCH_LEFT_DOWN  = 43,
  
  SIG_SINGLE_RIGHT  = 100, 
  SIG_SINGLE_LEFT   = 101, 
  SIG_DOUBLE_RIGHT  = 102, 
  SIG_DOUBLE_LEFT   = 103, 
# Each "TrackBlock" defines an 16x16 pixel block
# corresponding to a single track element

class MRBusPacket:
  def __init__(self, dest=0, src=0, cmd=0, data=0):
    self.dest=dest
    self.src=src
    self.cmd=cmd
    self.data=data
    
  def __hash__(self):
    return hash(repr(self))

  def __eq__(self, other):
    return repr(self)==repr(other)

  def __repr__(self):
    return "mrbus.packet(0x%02x, 0x%02x, 0x%02x, %s)"%(self.dest, self.src, self.cmd, repr(self.data))

  def __str__(self):
    c='(0x%02X'%self.cmd
    if self.cmd >= 32 and self.cmd <= 127:
      c+=" '%c')"%self.cmd
    else:
      c+="    )"
    return "packet(0x%02X->0x%02X) %s %2d:%s"%(self.src, self.dest, c, len(self.data), ["0x%02X"%d for d in self.data])

  @classmethod
  def fromJSON(cls, message):
    self = cls.__new__(cls)
    retval = self._fromJSON(message)
    if False == retval:
      print("packet didn't parse")
      return None
    return self    

  def _fromJSON(self, message):
    try:
      decodedValues = json.loads(message)
      if 'type' not in decodedValues or decodedValues['type'] != 'pkt':
        return False
      if 'src' not in decodedValues or 'dst' not in decodedValues or 'cmd' not in decodedValues or 'data' not in decodedValues:
        return False
      self.src = int(decodedValues['src'])
      self.dest = int(decodedValues['dst'])
      self.cmd = int(decodedValues['cmd'])
      self.data = []
      for d in decodedValues['data']:
        self.data.append(int(d))

    except:
      return False
      
    return True

class TrackBlock:
  name = "Unknown"
  trackType = TrackBlockType.HORIZONTAL
  x = -1
  y = -1
  cell_x = -1
  cell_y = -1
  cellSize = 16
  color = "#FFF"

  def __init__(self):
    pass

  def setXY(self, x, y):
    self.x = x * self.cellSize
    self.y = y * self.cellSize
    self.cell_x = x
    self.cell_y = y

  def setColor(self, color):
    self.color = color

  def getXY(self):
    return (self.cell_x, self.cell_y)


  def setType(self, trackType):
    self.trackType = trackType

  def draw(self, dc):
    dc.SetBrush(wx.Brush('#000'))
    dc.SetPen(wx.Pen("#000"))
    dc.DrawRectangle(self.x, self.y, self.cellSize, self.cellSize)

    dc.SetPen(wx.Pen(self.color, width=2))

    if self.trackType == TrackBlockType.HORIZONTAL:
      dc.DrawLine(self.x, self.y + (self.cellSize//2 - 1), self.x+self.cellSize-1, self.y + (self.cellSize//2 - 1))

    elif self.trackType == TrackBlockType.END_HORIZ_RIGHT:
      dc.DrawLine(self.x, self.y + (self.cellSize//2 - 1), self.x+self.cellSize-5, self.y + (self.cellSize//2 - 1))

    elif self.trackType == TrackBlockType.END_HORIZ_LEFT:
      dc.DrawLine(self.x+4, self.y + (self.cellSize//2 - 1), self.x+self.cellSize-1, self.y + (self.cellSize//2 - 1))


    elif self.trackType == TrackBlockType.DIAG_LEFT_UP:
      dc.DrawLine(self.x, self.y, self.x+self.cellSize-1, self.y+self.cellSize-1)

    elif self.trackType == TrackBlockType.DIAG_RIGHT_UP:
      dc.DrawLine(self.x+self.cellSize-1, self.y, self.x, self.y+self.cellSize-1)

    elif self.trackType == TrackBlockType.ANGLE_LEFT_UP:
      dc.DrawLine(self.x, self.y, self.x+(self.cellSize//2 - 1), self.y+(self.cellSize//2 - 1))
      dc.DrawLine(self.x+(self.cellSize//2 - 1), self.y + (self.cellSize//2 - 1), self.x + (self.cellSize - 1), self.y + (self.cellSize//2 - 1))

    elif self.trackType == TrackBlockType.ANGLE_LEFT_DOWN:
      dc.DrawLine(self.x, self.y + self.cellSize-1, self.x+(self.cellSize//2 - 1), self.y+(self.cellSize//2 - 1))
      dc.DrawLine(self.x+(self.cellSize//2 - 1), self.y + (self.cellSize//2 - 1), self.x + (self.cellSize - 1), self.y + (self.cellSize//2 - 1))

    elif self.trackType == TrackBlockType.ANGLE_RIGHT_UP:
      dc.DrawLine(self.x + self.cellSize - 1, self.y, self.x+(self.cellSize//2 - 1), self.y+(self.cellSize//2 - 1))
      dc.DrawLine(self.x+(self.cellSize//2 - 1), self.y + (self.cellSize//2 - 1), self.x, self.y + (self.cellSize//2 - 1))

    elif self.trackType == TrackBlockType.ANGLE_RIGHT_DOWN:
      dc.DrawLine(self.x + self.cellSize - 1, self.y + self.cellSize-1, self.x+(self.cellSize//2 - 1), self.y+(self.cellSize//2 - 1))
      dc.DrawLine(self.x+(self.cellSize//2 - 1), self.y + (self.cellSize//2 - 1), self.x, self.y + (self.cellSize//2 - 1))

class TextBlock(TrackBlock):
  def __init__(self):
    self.color = '#FFF'
    self.text = ""
    pass

  def setType(self, signalType):
    self.trackType = signalType
    
  def setText(self, text):
    self.text = text
    
  def draw(self, dc):
    dc.SetBrush(wx.Brush('#000'))
    dc.SetPen(wx.Pen("#000"))
    dc.DrawRectangle(self.x, self.y, self.cellSize, self.cellSize)

    dc.SetPen(wx.Pen(self.color, width=2))
    dc.SetBrush(wx.Brush(self.color))
    dc.SetTextForeground(self.color) 
    dc.DrawText(self.text, self.x, self.y)


class SignalBlock(TrackBlock):
  def __init__(self):
    self.color = '#F00'
    pass

  def setType(self, signalType):
    self.trackType = signalType
    
  def draw(self, dc):
    dc.SetBrush(wx.Brush('#000'))
    dc.SetPen(wx.Pen("#000"))
    dc.DrawRectangle(self.x, self.y, self.cellSize, self.cellSize)

    dc.SetPen(wx.Pen(self.color, width=2))
    dc.SetBrush(wx.Brush(self.color))
    
    if self.trackType == TrackBlockType.SIG_SINGLE_RIGHT:
      dc.DrawCircle(self.x + self.cellSize - 3, self.y + self.cellSize//2, 3)
      dc.SetBrush(wx.Brush('#000'))
      dc.DrawLine(self.x, self.y + self.cellSize//2, self.x + self.cellSize - 7, self.y + self.cellSize//2)
      dc.DrawLine(self.x, self.y + self.cellSize//2 - 4, self.x, self.y + self.cellSize//2 + 4)

    elif self.trackType == TrackBlockType.SIG_DOUBLE_RIGHT:
      dc.DrawCircle(self.x + self.cellSize - 3, self.y + self.cellSize//2, 3)
      dc.DrawCircle(self.x + self.cellSize - 9, self.y + self.cellSize//2, 3)
      dc.SetBrush(wx.Brush('#000'))
      dc.DrawLine(self.x, self.y + self.cellSize//2, self.x + self.cellSize - 7, self.y + self.cellSize//2)
      dc.DrawLine(self.x, self.y + self.cellSize//2 - 4, self.x, self.y + self.cellSize//2 + 4)

    elif self.trackType == TrackBlockType.SIG_SINGLE_LEFT:
      dc.DrawCircle(self.x + 3, self.y + self.cellSize//2, 3)
      dc.SetBrush(wx.Brush('#000'))
      dc.DrawLine(self.x + self.cellSize-1, self.y + self.cellSize//2, self.x + 6, self.y + self.cellSize//2)
      dc.DrawLine(self.x + self.cellSize-1, self.y + self.cellSize//2 - 4, self.x + self.cellSize-1, self.y + self.cellSize//2 + 4)

    elif self.trackType == TrackBlockType.SIG_DOUBLE_LEFT:
      dc.DrawCircle(self.x + 3, self.y + self.cellSize//2, 3)
      dc.DrawCircle(self.x + 9, self.y + self.cellSize//2, 3)
      dc.SetBrush(wx.Brush('#000'))
      dc.DrawLine(self.x + self.cellSize-1, self.y + self.cellSize//2, self.x + 6, self.y + self.cellSize//2)
      dc.DrawLine(self.x + self.cellSize-1, self.y + self.cellSize//2 - 4, self.x + self.cellSize-1, self.y + self.cellSize//2 + 4)
      
      
class SwitchBlock(TrackBlock):
  switchState = 0
  switchStatusColor = "#00FF00"
  def __init__(self):
    pass

  def setSwitchPosition(self, pos):
    self.switchState = pos

  def getSwitchPosition(self):
    return self.switchState

  def setSwitchStatusColor(self, color):
    self.switchStatusColor = color

  def draw(self, dc):
    dc.SetBrush(wx.Brush('#000'))
#    dc.SetPen(wx.Pen("#E1FCFF", width=1))
    dc.SetPen(wx.Pen("#000"))
    dc.DrawRectangle(self.x, self.y, self.cellSize, self.cellSize)

    dc.SetPen(wx.Pen(self.switchStatusColor, width=1))
    dc.DrawRectangle(self.x+2, self.y+2, self.cellSize-4, self.cellSize-4)
    dc.SetPen(wx.Pen(self.color, width=2))
    
    if self.trackType == TrackBlockType.SWITCH_RIGHT_DOWN:
      if self.switchState != 0:
        dc.DrawLine(self.x, self.y+(self.cellSize//2 - 1), self.x+(self.cellSize//2), self.y+(self.cellSize/2 - 1))
        dc.DrawLine(self.x+(self.cellSize//2), self.y+(self.cellSize/2 - 1), self.x+(self.cellSize - 1), self.y+(self.cellSize - 1))
      else:
        dc.DrawLine(self.x, self.y + (self.cellSize/2 - 1), self.x+self.cellSize-1, self.y + (self.cellSize/2 - 1))

    elif self.trackType == TrackBlockType.SWITCH_RIGHT_UP:
      if self.switchState != 0:
        dc.DrawLine(self.x, self.y+(self.cellSize//2 - 1), self.x+(self.cellSize//2), self.y+(self.cellSize//2 - 1))
        dc.DrawLine(self.x+(self.cellSize//2), self.y+(self.cellSize//2 - 1), self.x + (self.cellSize - 1), self.y)
      else:
        dc.DrawLine(self.x, self.y + (self.cellSize/2 - 1), self.x+self.cellSize-1, self.y + (self.cellSize/2 - 1))

    elif self.trackType == TrackBlockType.SWITCH_LEFT_DOWN:
      if self.switchState != 0:
        dc.DrawLine(self.x + (self.cellSize - 1), self.y+(self.cellSize//2 - 1), self.x+(self.cellSize//2), self.y+(self.cellSize//2 - 1))
        dc.DrawLine(self.x+(self.cellSize/2 - 1), self.y+(self.cellSize//2 - 1), self.x, self.y+(self.cellSize - 1))
      else:
        dc.DrawLine(self.x, self.y + (self.cellSize/2 - 1), self.x+self.cellSize-1, self.y + (self.cellSize/2 - 1))

    elif self.trackType == TrackBlockType.SWITCH_LEFT_UP:
      if self.switchState != 0:
        dc.DrawLine(self.x + (self.cellSize - 1), self.y+(self.cellSize//2 - 1), self.x+(self.cellSize//2), self.y+(self.cellSize/2 - 1))
        dc.DrawLine(self.x+(self.cellSize//2), self.y+(self.cellSize//2 - 1), self.x, self.y)
      else:
        dc.DrawLine(self.x, self.y + (self.cellSize/2 - 1), self.x+self.cellSize-1, self.y + (self.cellSize/2 - 1))

import re

class MRBusBit:
  def __init__(self, pattern=""):
    self.src = 0
    self.cmd = 0
    self.byte = 0
    self.bit = 0
    self.state = False
    if pattern is not "":
      self.fromPattern(pattern)

  # Changes the internal bit state if the packet matches
  # Returns true if this packet applied to us and changed our state
  def testPacket(self, pkt):
    oldState = self.state
    if self.src == pkt.src and self.cmd == pkt.cmd and len(pkt.data) >= self.byte:
      if (pkt.data[self.byte] & (1<<self.bit)) is not 0:
        self.state = True
      else:
        self.state = False
      if oldState is not self.state:
        return True
    return False
  
  def getState(self):
    return self.state
  
  def fromPattern(self, pattern):
    m = re.match("(0x[0-9A-Za-z]{2}),([0-9A-Za-z]{1}),(\d+):(\d+)", pattern)
    if m is not None:
      self.src = int(m.group(1), 0)
      self.cmd = ord(m.group(2))
      self.byte = int(m.group(3))-6
      self.bit = int(m.group(4))
      return True

    print("Pattern did not match")
    return False

def relCoord(base_x, newVal):
  newVal = str(newVal)
  m = re.match('^\+([0-9].*)', newVal)
  if m is not None:
    retval = base_x + int(m.group(0))
    #print("relCoord pos base=%d newVal=[%s] newval=%d" % (base_x, newVal, retval))
    return retval

  m = re.match('^-([0-9].*)', newVal)
  if m is not None:
    retval = base_x + int(m.group(0))
    #print("relCoord neg base=%d newVal=[%s] newval=%d" % (base_x, newVal, retval))
    return retval
  
  return int(newVal)

import datetime

class MqttMRBus:
  incomingPkts = queue.Queue(maxsize=500)
  outgoingPkts = queue.Queue(maxsize=500)
  def __init__(self):
    pass

class Example(wx.Frame):
  cells = []
  blocks = [ ]
  signals = []
  switches = []
  menuHeight = 0
  currentBlockType = 0
  gridOn = False
  layoutData = None
  pktTimer = None
  timerCnt = 0

  def __init__(self, railroadLayoutData, mqttMRBus):
    super(Example, self).__init__(None)
    self.layoutData = railroadLayoutData
    self.InitUI()

    self.mqttMRBus = mqttMRBus

    self.pktTimer = wx.Timer(self, 1)
    self.Bind(wx.EVT_TIMER, self.OnTimer)
    self.pktTimer.Start(100)


  def doDisplayUpdate(self):
    dc = wx.ClientDC(self)
    updatesToApply = False
    for i in range(0, len(self.blocks)):
      block = self.blocks[i]
#      print("block %d [%s] isUpdated = [%s]" % (i, block['name'], block['isUpdated']))
      if False == block['isUpdated']:
        continue
      updatesToApply = True

      for cell in block['cells']:
        cell.draw(dc)

      self.blocks[i]['isUpdated'] = False

    if updatesToApply:

      self.Update()
   
  
  def applyPacket(self, pkt):
    for i in range(0, len(self.blocks)):
      block = self.blocks[i]
      #print("block %d [%s] isUpdated = [%s]" % (i, block['name'], block['isUpdated']))
      if block['occupancy'].testPacket(pkt):
        if block['occupancy'].getState():
          color = '#F00'
        else:
          color = '#FFF'

        for cell in block['cells']:
            cell.setColor(color)

        self.blocks[i]['isUpdated'] = True
    self.doDisplayUpdate()

  def OnTimer(self, event):
    self.timerCnt += 1
#    ptstr = "LC at %u,%u - block %ux%u" % (x,y, block_x, block_y)
    ptstr = "tmrcnt = %u pktcnt=%d" % (self.timerCnt, self.mqttMRBus.incomingPkts.qsize())

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
      newCell = TextBlock()
      newCell.setText(text['value'])
      newCell.setXY(int(text['x']), int(text['y']))
      self.cells.append(newCell)

    for signal in self.layoutData['signals']:
      newSignal = { }
      newSignal['cells'] = []
      newSignal['isUpdated'] = True
      if "name" in signal.keys():
        newSignal['name'] = signal['name']
      else:
        newSignal['name'] = "Unknown"
      newCell = SignalBlock()
      newCell.setXY(int(signal['x']), int(signal['y']))

      cellType = {
        'signal_left':TrackBlockType.SIG_SINGLE_LEFT,
        'signal_right':TrackBlockType.SIG_SINGLE_RIGHT,
      }
      
      if signal['type'] in cellType.keys():
        newCell.setType(cellType[signal['type']])

      self.cells.append(newCell)
      newSignal['cells'].append(newCell)
      self.signals.append(newSignal)

    for switch in self.layoutData['switches']:
      newSwitch = { }
      newSwitch['cells'] = []
      newSwitch['isUpdated'] = True
      if "name" in switch.keys():
        newSwitch['name'] = switch['name']
      else:
        newSwitch['name'] = "Unknown"

      newCell = SwitchBlock()
      newCell.setXY(int(switch['x']), int(switch['y']))

      cellType = {
        'switch_right_down':TrackBlockType.SWITCH_RIGHT_DOWN,
        'switch_right_up':TrackBlockType.SWITCH_RIGHT_UP,
        'switch_left_down':TrackBlockType.SWITCH_LEFT_DOWN,
        'switch_left_up':TrackBlockType.SWITCH_LEFT_UP,
      }
      
      if switch['type'] in cellType.keys():
        print("Placing cell of type [%s] at (%d,%d)" % (switch['type'], int(switch['x']), int(switch['y'])))
        newCell.setType(cellType[switch['type']])
      else:
        print("Did not understand switch type [%s]" % (switch['type']))

      self.cells.append(newCell)
      newSwitch['cells'].append(newCell)
      self.switches.append(newSwitch)



    for block in self.layoutData['blocks']:
      newBlock = { }
      newBlock['cells'] = []
      newBlock['isUpdated'] = True
      if "blockName" in block.keys():
        newBlock['name'] = block['blockName']
      else:
        newBlock['name'] = "Unknown"

      if "occupancy" in block.keys():
        newBlock['occupancy'] = MRBusBit(block['occupancy'])

      base_x = 0
      base_y = 0
      
      if "base_x" in block.keys():
        newBlock['base_x'] = int(block['base_x'])
        base_x = newBlock['base_x']

      if "base_y" in block.keys():
        newBlock['base_y'] = int(block['base_y'])
        base_y = newBlock['base_y']


      for cell in block['cells']:
        x = relCoord(base_x, cell['x'])
        y = relCoord(base_y, cell['y'])

        if 'x_end' in cell.keys():
          x_end = relCoord(base_x, cell['x_end']) + 1
        else:
          x_end = x + 1

        if 'y_end' in cell.keys():
          y_end = relCoord(base_y, cell['y_end']) + 1
        else:
          y_end = y + 1

        for cell_x in range(x, x_end):
          for cell_y in range(y, y_end):
            if self.isSwitchCell(cell['type']):
              newCell = SwitchBlock()
            elif self.isSignalCell(cell['type']):
              newCell = SignalBlock()
            else:
              newCell = TrackBlock()
              
              cellType = {
                'horiz':TrackBlockType.HORIZONTAL,
                'diag_right_up':TrackBlockType.DIAG_RIGHT_UP,
                'diag_left_up':TrackBlockType.DIAG_LEFT_UP,
                'angle_left_down':TrackBlockType.ANGLE_LEFT_DOWN,
                'angle_left_up':TrackBlockType.ANGLE_LEFT_UP,
                'angle_right_down':TrackBlockType.ANGLE_RIGHT_DOWN,
                'angle_right_up':TrackBlockType.ANGLE_RIGHT_UP,
                'horiz_rightgap':TrackBlockType.END_HORIZ_RIGHT,
                'horiz_leftgap':TrackBlockType.END_HORIZ_LEFT,
              }

              newCell.setXY(cell_x, cell_y)
              if cell['type'] in cellType.keys():
                print("Placing cell of type [%s] at (%d,%d)" % (cell['type'], cell_x, cell_y))
                newCell.setType(cellType[cell['type']])
              else:
                print("Warnings - cell type %s not known at (%d,%d)" % (cell['type'], x, y))

              self.cells.append(newCell)
              newBlock['cells'].append(newCell)
      self.blocks.append(newBlock)
      
    # and a status bar
    self.CreateStatusBar()
    self.SetStatusText("Welcome to wxPython!")


  def OnLeftDown(self, e):
    x,y = e.GetPosition()
    block_x = x//16
    block_y = y//16
    
    ptstr = "LC at %u,%u - block %ux%u" % (x,y, block_x, block_y)
    self.SetStatusText(ptstr)
    
    if self.editMenu.IsChecked(1):
      # Edit Mode
      for cell in self.cells:
        # Remove anything at this position
        if (block_x,block_y) == cell.getXY():
          self.blocks.remove(cell)

      

      dc = wx.PaintDC(self)
      (size_x, size_y) = self.GetSize()
      dc.SetBackground(wx.Brush('#000'))
      dc.Clear()

      dc.SetBrush(wx.Brush('#000'))
      dc.SetPen(wx.Pen("#FFF", width=2))

      for cell in self.cells:
        cell.draw(dc)

      
    else:
      dc = wx.PaintDC(self)
      self.cells[0].setSwitchPosition([1,0][self.cells[0].getSwitchPosition()])
      self.cells[0].draw(wx.PaintDC(self))

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
  ex = Example(layoutData, mqttMRBus)
  ex.Show()
  app.MainLoop()


if __name__ == '__main__':
  main()

