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

# Each "TrackBlock" defines an 8x8 pixel block
# corresponding to a single track element

class TrackBlock:
  name = "Unknown"
  trackType = 1
  x = -1
  y = -1
  blockSize = 16

  def __init__(self):
    pass

  def setXY(self, x, y):
    self.x = x * self.blockSize
    self.y = y * self.blockSize

  def setType(self, trackType):
    self.trackType = trackType

  def draw(self, dc):
    dc.SetBrush(wx.Brush('#000'))
    dc.SetPen(wx.Pen("#000"))
    dc.DrawRectangle(self.x, self.y, self.blockSize, self.blockSize)

    dc.SetPen(wx.Pen("#FFF", width=2))

    if self.trackType == 1:
      dc.DrawLine(self.x, self.y + (self.blockSize/2 - 1), self.x+self.blockSize-1, self.y + (self.blockSize/2 - 1))
    elif self.trackType == 2:
      dc.DrawLine(self.x, self.y, self.x+self.blockSize-1, self.y+self.blockSize-1)
    elif self.trackType == 3:
      dc.DrawLine(self.x+self.blockSize-1, self.y+self.blockSize-1, self.x, self.y)
    elif self.trackType == 4:
      dc.DrawLine(self.x, self.y, self.x+(self.blockSize/2 - 1), self.y+(self.blockSize/2 - 1))
      dc.DrawLine(self.x+(self.blockSize/2 - 1), self.y + (self.blockSize/2 - 1), self.x + (self.blockSize - 1), self.y + (self.blockSize/2 - 1))
    elif self.trackType == 5:
      dc.DrawLine(self.x, self.y + (self.blockSize/2 - 1), self.x+self.blockSize-1, self.y + (self.blockSize/2 - 1))
      dc.SetPen(wx.Pen("#FFF", width=1))
      dc.DrawLine(self.x+1, self.y + (self.blockSize/4)-1, self.x+1, self.y + 3*(self.blockSize/4))
    elif self.trackType == 6:
      dc.DrawLine(self.x, self.y + (self.blockSize/2 - 1), self.x+self.blockSize-1, self.y + (self.blockSize/2 - 1))
      dc.SetPen(wx.Pen("#FFF", width=1))
      dc.DrawLine(self.x+self.blockSize-1, self.y + (self.blockSize/4)-1, self.x+self.blockSize-1, self.y + 3*(self.blockSize/4))



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
    dc.SetPen(wx.Pen("#00FF00", width=1))
    dc.DrawRectangle(self.x+2, self.y+2, self.blockSize-4, self.blockSize-4)
    dc.SetPen(wx.Pen("#FFF", width=2))
    if self.switchState != 0:
      dc.DrawLine(self.x+1, self.y+(self.blockSize/2 - 1), self.x+(self.blockSize/2 - 1), self.y+(self.blockSize/2 - 1))
      dc.DrawLine(self.x+(self.blockSize/2 - 1), self.y+(self.blockSize/2 - 1), self.x+(self.blockSize - 1), self.y+(self.blockSize - 1))
    else:
      dc.DrawLine(self.x+1, self.y + (self.blockSize/2 - 1), self.x+self.blockSize-1, self.y + (self.blockSize/2 - 1))



class Example(wx.Frame):
  blocks = []
  menuHeight = 0
  currentBlockType = 0
  gridOn = True

  def __init__(self, *args, **kw):
    super(Example, self).__init__(*args, **kw)
    self.InitUI()

  def InitUI(self):
    self.Bind(wx.EVT_PAINT, self.OnPaint)
    self.Bind(wx.EVT_SIZE, self.OnPaint)
    self.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
    self.SetTitle("CRNW Dispatch System")
    self.SetSize((750,500))
    self.Centre()
    self.Show(True)
    # create a menu bar
    self.makeMenuBar()

    switchBlock = SwitchBlock()
    switchBlock.setXY(1, 1)
    self.blocks.append(switchBlock)

    trackBlock = TrackBlock()
    trackBlock.setXY(3, 1)
    self.blocks.append(trackBlock)

    trackBlock = TrackBlock()
    trackBlock.setXY(2, 2)
    trackBlock.setType(2)
    self.blocks.append(trackBlock)

    trackBlock = TrackBlock()
    trackBlock.setXY(3, 3)
    trackBlock.setType(4)
    self.blocks.append(trackBlock)

    trackBlock = TrackBlock()
    trackBlock.setXY(2, 1)
    self.blocks.append(trackBlock)

    trackBlock = TrackBlock()
    trackBlock.setXY(3, 1)
    self.blocks.append(trackBlock)


    trackBlock = TrackBlock()
    trackBlock.setXY(4, 1)
    trackBlock.setType(5)
    self.blocks.append(trackBlock)

    trackBlock = TrackBlock()
    trackBlock.setXY(4, 3)
    trackBlock.setType(5)
    self.blocks.append(trackBlock)


    # and a status bar
    self.CreateStatusBar()
    self.SetStatusText("Welcome to wxPython!")

  def OnLeftDown(self, e):
    dc = wx.ClientDC(self)
    x,y = e.GetPosition()
    ptstr = "LC at %u,%u - block %ux%u" % (x,y, x/(16), y/(16))
    self.SetStatusText(ptstr)

    


    self.blocks[0].setSwitchPosition([1,0][self.blocks[0].getSwitchPosition()])
    self.blocks[0].draw(wx.PaintDC(self))

  def OnPaint(self, e):
    #dc = wx.ClientDC(self)
    dc = wx.PaintDC(self)
    (size_x, size_y) = self.GetSize()
    dc.SetBackground(wx.Brush('#000'))
    dc.Clear()

    dc.SetBrush(wx.Brush('#000'))
    if self.gridOn:
      dc.SetPen(wx.Pen("#AAA", width=1))
      for x in range(0, size_x/16):
        for y in range(0, size_y/16):
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


def main():


  app = wx.App()
  ex = Example(None)
  ex.Show()
  app.MainLoop()


if __name__ == '__main__':
  main()

