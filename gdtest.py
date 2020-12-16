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

import wx
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

class TrackBlock:
  name = "Unknown"
  trackType = TrackBlockType.HORIZONTAL
  x = -1
  y = -1
  block_x = -1
  block_y = -1
  blockSize = 16

  def __init__(self):
    pass

  def setXY(self, x, y):
    self.x = x * self.blockSize
    self.y = y * self.blockSize
    self.block_x = x
    self.block_y = y

  def getXY(self):
    return (self.block_x, self.block_y)


  def setType(self, trackType):
    self.trackType = trackType

  def draw(self, dc):
    dc.SetBrush(wx.Brush('#000'))
    dc.SetPen(wx.Pen("#000"))
    dc.DrawRectangle(self.x, self.y, self.blockSize, self.blockSize)

    dc.SetPen(wx.Pen("#FFF", width=2))

    if self.trackType == TrackBlockType.HORIZONTAL:
      dc.DrawLine(self.x, self.y + (self.blockSize//2 - 1), self.x+self.blockSize-1, self.y + (self.blockSize//2 - 1))

    elif self.trackType == TrackBlockType.END_HORIZ_RIGHT:
      dc.DrawLine(self.x, self.y + (self.blockSize//2 - 1), self.x+self.blockSize-5, self.y + (self.blockSize//2 - 1))

    elif self.trackType == TrackBlockType.END_HORIZ_LEFT:
      dc.DrawLine(self.x+4, self.y + (self.blockSize//2 - 1), self.x+self.blockSize-1, self.y + (self.blockSize//2 - 1))


    elif self.trackType == TrackBlockType.DIAG_LEFT_UP:
      dc.DrawLine(self.x, self.y, self.x+self.blockSize-1, self.y+self.blockSize-1)

    elif self.trackType == TrackBlockType.DIAG_RIGHT_UP:
      dc.DrawLine(self.x+self.blockSize-1, self.y, self.x, self.y+self.blockSize-1)

    elif self.trackType == TrackBlockType.ANGLE_LEFT_UP:
      dc.DrawLine(self.x, self.y, self.x+(self.blockSize//2 - 1), self.y+(self.blockSize//2 - 1))
      dc.DrawLine(self.x+(self.blockSize//2 - 1), self.y + (self.blockSize//2 - 1), self.x + (self.blockSize - 1), self.y + (self.blockSize//2 - 1))

    elif self.trackType == TrackBlockType.ANGLE_LEFT_DOWN:
      dc.DrawLine(self.x, self.y + self.blockSize-1, self.x+(self.blockSize//2 - 1), self.y+(self.blockSize//2 - 1))
      dc.DrawLine(self.x+(self.blockSize//2 - 1), self.y + (self.blockSize//2 - 1), self.x + (self.blockSize - 1), self.y + (self.blockSize//2 - 1))

    elif self.trackType == TrackBlockType.ANGLE_RIGHT_UP:
      dc.DrawLine(self.x + self.blockSize - 1, self.y + self.blockSize-1, self.x+(self.blockSize//2 - 1), self.y+(self.blockSize//2 - 1))
      dc.DrawLine(self.x+(self.blockSize//2 - 1), self.y + (self.blockSize//2 - 1), self.x, self.y + (self.blockSize//2 - 1))

    elif self.trackType == TrackBlockType.ANGLE_RIGHT_DOWN:
      dc.DrawLine(self.x + self.blockSize - 1, self.y, self.x+(self.blockSize//2 - 1), self.y+(self.blockSize//2 - 1))
      dc.DrawLine(self.x+(self.blockSize//2 - 1), self.y + (self.blockSize//2 - 1), self.x, self.y + (self.blockSize//2 - 1))

class SignalBlock(TrackBlock):
  def __init__(self):
    pass

  def setType(self, signalType):
    self.trackType = signalType
    
  def draw(self, dc):
    dc.SetBrush(wx.Brush('#000'))
    dc.SetPen(wx.Pen("#000"))
    dc.DrawRectangle(self.x, self.y, self.blockSize, self.blockSize)

    dc.SetPen(wx.Pen("#F00", width=2))
    dc.SetBrush(wx.Brush('#F00'))
    
    if self.trackType == TrackBlockType.SIG_SINGLE_RIGHT:
      dc.DrawCircle(self.x + self.blockSize - 3, self.y + self.blockSize//2, 3)
      dc.SetBrush(wx.Brush('#000'))
      dc.DrawLine(self.x, self.y + self.blockSize//2, self.x + self.blockSize - 7, self.y + self.blockSize//2)
      dc.DrawLine(self.x, self.y + self.blockSize//2 - 4, self.x, self.y + self.blockSize//2 + 4)

    elif self.trackType == TrackBlockType.SIG_DOUBLE_RIGHT:
      dc.DrawCircle(self.x + self.blockSize - 3, self.y + self.blockSize//2, 3)
      dc.DrawCircle(self.x + self.blockSize - 9, self.y + self.blockSize//2, 3)
      dc.SetBrush(wx.Brush('#000'))
      dc.DrawLine(self.x, self.y + self.blockSize//2, self.x + self.blockSize - 7, self.y + self.blockSize//2)
      dc.DrawLine(self.x, self.y + self.blockSize//2 - 4, self.x, self.y + self.blockSize//2 + 4)

    elif self.trackType == TrackBlockType.SIG_SINGLE_LEFT:
      dc.DrawCircle(self.x + 3, self.y + self.blockSize//2, 3)
      dc.SetBrush(wx.Brush('#000'))
      dc.DrawLine(self.x + self.blockSize-1, self.y + self.blockSize//2, self.x + 6, self.y + self.blockSize//2)
      dc.DrawLine(self.x + self.blockSize-1, self.y + self.blockSize//2 - 4, self.x + self.blockSize-1, self.y + self.blockSize//2 + 4)

    elif self.trackType == TrackBlockType.SIG_DOUBLE_LEFT:
      dc.DrawCircle(self.x + 3, self.y + self.blockSize//2, 3)
      dc.DrawCircle(self.x + 9, self.y + self.blockSize//2, 3)
      dc.SetBrush(wx.Brush('#000'))
      dc.DrawLine(self.x + self.blockSize-1, self.y + self.blockSize//2, self.x + 6, self.y + self.blockSize//2)
      dc.DrawLine(self.x + self.blockSize-1, self.y + self.blockSize//2 - 4, self.x + self.blockSize-1, self.y + self.blockSize//2 + 4)
      
      
class SwitchBlock(TrackBlock):
  switchState = 0
  def __init__(self):
    pass

  def setSwitchPosition(self, pos):
    self.switchState = pos

  def getSwitchPosition(self):
    return self.switchState

  def draw(self, dc):
    dc.SetBrush(wx.Brush('#000'))
#    dc.SetPen(wx.Pen("#E1FCFF", width=1))
    dc.SetPen(wx.Pen("#000"))
    dc.DrawRectangle(self.x, self.y, self.blockSize, self.blockSize)

    dc.SetPen(wx.Pen("#00FF00", width=1))
    dc.DrawRectangle(self.x+2, self.y+2, self.blockSize-4, self.blockSize-4)
    dc.SetPen(wx.Pen("#FFF", width=2))
    
    if self.trackType == TrackBlockType.SWITCH_RIGHT_DOWN:
      if self.switchState != 0:
        dc.DrawLine(self.x, self.y+(self.blockSize//2 - 1), self.x+(self.blockSize//2), self.y+(self.blockSize/2 - 1))
        dc.DrawLine(self.x+(self.blockSize//2), self.y+(self.blockSize/2 - 1), self.x+(self.blockSize - 1), self.y+(self.blockSize - 1))
      else:
        dc.DrawLine(self.x, self.y + (self.blockSize/2 - 1), self.x+self.blockSize-1, self.y + (self.blockSize/2 - 1))

    elif self.trackType == TrackBlockType.SWITCH_RIGHT_UP:
      if self.switchState != 0:
        dc.DrawLine(self.x, self.y+(self.blockSize//2 - 1), self.x+(self.blockSize//2), self.y+(self.blockSize//2 - 1))
        dc.DrawLine(self.x+(self.blockSize//2), self.y+(self.blockSize//2 - 1), self.x + (self.blockSize - 1), self.y)
      else:
        dc.DrawLine(self.x, self.y + (self.blockSize/2 - 1), self.x+self.blockSize-1, self.y + (self.blockSize/2 - 1))

    elif self.trackType == TrackBlockType.SWITCH_LEFT_DOWN:
      if self.switchState != 0:
        dc.DrawLine(self.x + (self.blockSize - 1), self.y+(self.blockSize//2 - 1), self.x+(self.blockSize//2), self.y+(self.blockSize//2 - 1))
        dc.DrawLine(self.x+(self.blockSize/2 - 1), self.y+(self.blockSize//2 - 1), self.x, self.y+(self.blockSize - 1))
      else:
        dc.DrawLine(self.x, self.y + (self.blockSize/2 - 1), self.x+self.blockSize-1, self.y + (self.blockSize/2 - 1))

    elif self.trackType == TrackBlockType.SWITCH_LEFT_UP:
      if self.switchState != 0:
        dc.DrawLine(self.x + (self.blockSize - 1), self.y+(self.blockSize//2 - 1), self.x+(self.blockSize//2), self.y+(self.blockSize/2 - 1))
        dc.DrawLine(self.x+(self.blockSize//2), self.y+(self.blockSize//2 - 1), self.x, self.y)
      else:
        dc.DrawLine(self.x, self.y + (self.blockSize/2 - 1), self.x+self.blockSize-1, self.y + (self.blockSize/2 - 1))


class Example(wx.Frame):
  blocks = []
  menuHeight = 0
  currentBlockType = 0
  gridOn = False

  def __init__(self, *args, **kw):
    super(Example, self).__init__(*args, **kw)
    self.InitUI()

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

   # switchBlock = SwitchBlock()
   # switchBlock.setXY(1, 1)
   # self.blocks.append(switchBlock)

    trackBlock = SwitchBlock()
    trackBlock.setXY(3, 3)
    trackBlock.setType(TrackBlockType.SWITCH_RIGHT_UP)
    self.blocks.append(trackBlock)

    trackBlock = TrackBlock()
    trackBlock.setXY(4, 2)
    trackBlock.setType(TrackBlockType.DIAG_RIGHT_UP)
    self.blocks.append(trackBlock)

    trackBlock = TrackBlock()
    trackBlock.setXY(5, 1)
    trackBlock.setType(TrackBlockType.ANGLE_LEFT_DOWN)
    self.blocks.append(trackBlock)

    trackBlock = TrackBlock()
    trackBlock.setXY(6, 1)
    trackBlock.setType(TrackBlockType.END_HORIZ_RIGHT)
    self.blocks.append(trackBlock)

    trackBlock = TrackBlock()
    trackBlock.setXY(6, 3)
    trackBlock.setType(TrackBlockType.END_HORIZ_RIGHT)
    self.blocks.append(trackBlock)

    trackBlock = TrackBlock()
    trackBlock.setXY(7, 1)
    trackBlock.setType(TrackBlockType.HORIZONTAL)
    self.blocks.append(trackBlock)

    trackBlock = TrackBlock()
    trackBlock.setXY(7, 3)
    trackBlock.setType(TrackBlockType.HORIZONTAL)
    self.blocks.append(trackBlock)



    signalBlock = SignalBlock()
    signalBlock.setXY(6, 2)
    signalBlock.setType(TrackBlockType.SIG_SINGLE_LEFT)
    self.blocks.append(signalBlock)

    signalBlock = SignalBlock()
    signalBlock.setXY(6, 0)
    signalBlock.setType(TrackBlockType.SIG_SINGLE_LEFT)
    self.blocks.append(signalBlock)
    
    signalBlock = SignalBlock()
    signalBlock.setXY(2, 4)
    signalBlock.setType(TrackBlockType.SIG_SINGLE_RIGHT)
    self.blocks.append(signalBlock)

    trackBlock = TrackBlock()
    trackBlock.setXY(1, 3)
    trackBlock.setType(TrackBlockType.HORIZONTAL)
    self.blocks.append(trackBlock)

    trackBlock = TrackBlock()
    trackBlock.setXY(2, 3)
    trackBlock.setType(TrackBlockType.END_HORIZ_LEFT)
    self.blocks.append(trackBlock)



    trackBlock = TrackBlock()
    trackBlock.setXY(4, 3)
    trackBlock.setType(TrackBlockType.HORIZONTAL)
    self.blocks.append(trackBlock)

    trackBlock = TrackBlock()
    trackBlock.setXY(5, 3)
    trackBlock.setType(TrackBlockType.HORIZONTAL)
    self.blocks.append(trackBlock)





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
      for block in self.blocks:
        # Remove anything at this position
        if (block_x,block_y) == block.getXY():
          self.blocks.remove(block)

      

      dc = wx.ClientDC(self)
      (size_x, size_y) = self.GetSize()
      dc.SetBackground(wx.Brush('#000'))
      dc.Clear()

      dc.SetBrush(wx.Brush('#000'))
      dc.SetPen(wx.Pen("#FFF", width=2))

      for block in self.blocks:
        block.draw(dc)

      
    else:
      dc = wx.ClientDC(self)
      self.blocks[0].setSwitchPosition([1,0][self.blocks[0].getSwitchPosition()])
      self.blocks[0].draw(wx.ClientDC(self))

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

    for block in self.blocks:
      block.draw(dc)





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

    # Make an edit menu
    editMenu = wx.Menu()
    self.editMenu = editMenu
    enableEditItem = editMenu.AppendCheckItem(1, "&Enable Editing",
      "Enables panel editing")
    editMenu.AppendSeparator()
    
    drawTrackSubmenu = wx.Menu()
    drawTrackSubmenu.AppendRadioItem(1, "Blank")
    drawTrackSubmenu.AppendRadioItem(2, "Horizontal")
    drawTrackSubmenu.AppendRadioItem(3, "Diag - Right Up")
    drawTrackSubmenu.AppendRadioItem(4, "Diag - Left Up")
    self.drawTrackSubmenu = drawTrackSubmenu
    editMenu.AppendSubMenu(drawTrackSubmenu, "Draw")

    
    # Make the menu bar and add the two menus to it. The '&' defines
    # that the next letter is the "mnemonic" for the menu item. On the
    # platforms that support it those letters are underlined and can be
    # triggered from the keyboard.
    menuBar = wx.MenuBar()
    menuBar.Append(fileMenu, "&File")
    menuBar.Append(editMenu, "&Edit")
    menuBar.Append(helpMenu, "&Help")


    

    # Give the menu bar to the frame
    self.SetMenuBar(menuBar)

    # Finally, associate a handler function with the EVT_MENU event for
    # each of the menu items. That means that when that menu item is
    # activated then the associated handler function will be called.
    self.Bind(wx.EVT_MENU, self.OnHello, helloItem)
    self.Bind(wx.EVT_MENU, self.OnEnableEdit, enableEditItem)
    self.Bind(wx.EVT_MENU, self.OnExit,  exitItem)
    self.Bind(wx.EVT_MENU, self.OnAbout, aboutItem)

  def OnExit(self, event):
    """Close the frame, terminating the application."""
    self.Close(True)


  def OnHello(self, event):
    """Say hello to the user."""
    wx.MessageBox("Hello again from wxPython")

  def OnEnableEdit(self, event):
    # The checked indicator is the state we're going into
    if self.editMenu.IsChecked(1):
      ret = wx.MessageBox("Are you sure you want to enable editing?", "Enable Editing", wx.OK | wx.CANCEL | wx.ICON_WARNING)
      if ret != wx.OK:
        self.editMenu.Check(1, False)
      else:
        # Enable draw options
        pass
      
    

  def OnAbout(self, event):
    """Display an About Dialog"""
    wx.MessageBox("This is a wxPython Hello World sample",
      "About Hello World 2",
      wx.OK|wx.ICON_INFORMATION)


def main():


  app = wx.App()
  ex = Example(None)
  ex.Show()
  app.MainLoop()


if __name__ == '__main__':
  main()

