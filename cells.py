from enum import Enum
import wx

class TrackCellType(Enum):
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
# Each "TrackCell" defines an 16x16 pixel block
# corresponding to a single track element

class TrackCellColors:
  @staticmethod
  def getColor(itemName):
    colors = {
      'track_occupied':'#ff0000',
      'track_idle'    :'#ffffff',
      'track_lined'   :'#00ff00',
      'track_manual'  :'#00ccff',
      'track_unknown' :'#cccccc',
      'track_nopower' :'#ffd700',
      'switch_locked' :'#ff0000',
      'switch_normal' :'#00ff00',
      'switch_manual' :'#00ccff',
      'switch_unknown':'#cccccc',
      'signal_blinkoff':'#777777',
      'signal_lined'  :'#00ff00',
      'signal_normal' :'#ff0000',
      'signal_unknown':'#cccccc',
      'default'       :'#cccccc',
    }
    if itemName in colors.keys():
      return colors[itemName]
    return colors['default']



class TrackCell:
  def __init__(self):
    self.name = "Unknown"
    self.owner = None
    self.trackType = TrackCellType.HORIZONTAL
    self.x = -1
    self.y = -1
    self.cell_x = -1
    self.cell_y = -1
    self.cellSize = 16
    self.color = "#FFF"
    self.changedSinceRefresh = True

  def setXY(self, x, y):
    self.x = x * self.cellSize
    self.y = y * self.cellSize
    self.cell_x = x
    self.cell_y = y

  def setOwner(self, owner):
    self.owner = owner

  def setColor(self, color):
    if color != self.color:
      self.changedSinceRefresh = True
      self.color = color

  def getXY(self):
    return (self.cell_x, self.cell_y)

  def needsRedraw(self):
    return self.changedSinceRefresh

  def setType(self, trackType):
    if self.trackType != trackType:
      self.changedSinceRefresh = True
      self.trackType = trackType

  def getType(self):
    return self.trackType

  def draw(self, dc):
    dc.SetBrush(wx.Brush('#000'))
    dc.SetPen(wx.Pen("#000"))
    dc.DrawRectangle(self.x, self.y, self.cellSize, self.cellSize)

    dc.SetPen(wx.Pen(self.color, width=2))

    if self.trackType == TrackCellType.HORIZONTAL:
      dc.DrawLine(self.x, self.y + (self.cellSize//2 - 1), self.x+self.cellSize-1, self.y + (self.cellSize//2 - 1))

    elif self.trackType == TrackCellType.END_HORIZ_RIGHT:
      dc.DrawLine(self.x, self.y + (self.cellSize//2 - 1), self.x+self.cellSize-5, self.y + (self.cellSize//2 - 1))

    elif self.trackType == TrackCellType.END_HORIZ_LEFT:
      dc.DrawLine(self.x+4, self.y + (self.cellSize//2 - 1), self.x+self.cellSize-1, self.y + (self.cellSize//2 - 1))


    elif self.trackType == TrackCellType.DIAG_LEFT_UP:
      dc.DrawLine(self.x, self.y, self.x+self.cellSize-1, self.y+self.cellSize-1)

    elif self.trackType == TrackCellType.DIAG_RIGHT_UP:
      dc.DrawLine(self.x+self.cellSize-1, self.y, self.x, self.y+self.cellSize-1)

    elif self.trackType == TrackCellType.ANGLE_LEFT_UP:
      dc.DrawLine(self.x, self.y, self.x+(self.cellSize//2 - 1), self.y+(self.cellSize//2 - 1))
      dc.DrawLine(self.x+(self.cellSize//2 - 1), self.y + (self.cellSize//2 - 1), self.x + (self.cellSize - 1), self.y + (self.cellSize//2 - 1))

    elif self.trackType == TrackCellType.ANGLE_LEFT_DOWN:
      dc.DrawLine(self.x, self.y + self.cellSize-1, self.x+(self.cellSize//2 - 1), self.y+(self.cellSize//2 - 1))
      dc.DrawLine(self.x+(self.cellSize//2 - 1), self.y + (self.cellSize//2 - 1), self.x + (self.cellSize - 1), self.y + (self.cellSize//2 - 1))

    elif self.trackType == TrackCellType.ANGLE_RIGHT_UP:
      dc.DrawLine(self.x + self.cellSize - 1, self.y, self.x+(self.cellSize//2 - 1), self.y+(self.cellSize//2 - 1))
      dc.DrawLine(self.x+(self.cellSize//2 - 1), self.y + (self.cellSize//2 - 1), self.x, self.y + (self.cellSize//2 - 1))

    elif self.trackType == TrackCellType.ANGLE_RIGHT_DOWN:
      dc.DrawLine(self.x + self.cellSize - 1, self.y + self.cellSize-1, self.x+(self.cellSize//2 - 1), self.y+(self.cellSize//2 - 1))
      dc.DrawLine(self.x+(self.cellSize//2 - 1), self.y + (self.cellSize//2 - 1), self.x, self.y + (self.cellSize//2 - 1))

    self.changedSinceRefresh = False

class TextCell(TrackCell):
  def __init__(self):
    super().__init__()
    self.color = '#FFF'
    self.text = ""
    pass
    
  def setType(self, signalType):
    if self.trackType != signalType:
      self.trackType = signalType
      self.changedSinceRefresh = True
    
  def setText(self, text):
    if text != self.text:
      self.text = text
      self.changedSinceRefresh = True

  def draw(self, dc):
    dc.SetBrush(wx.Brush('#000'))
    dc.SetPen(wx.Pen("#000"))
    dc.DrawRectangle(self.x, self.y, self.cellSize, self.cellSize)

    dc.SetPen(wx.Pen(self.color, width=2))
    dc.SetBrush(wx.Brush(self.color))
    dc.SetTextForeground(self.color) 
    dc.DrawText(self.text, self.x, self.y)
    self.changedSinceRefresh = False

class SignalCell(TrackCell):
  def __init__(self):
    super().__init__()
    self.color = '#F00'
    self.blinky = False
    self.blinkState = False

  def setColor(self, color, blinky=False):
    if color != self.color:
      self.changedSinceRefresh = True
      self.color = color
    if blinky != self.blinky:
      self.blinky = blinky
      self.changedSinceRefresh = True

  def isBlinky(self):
    return self.blinky

  def setBlinkState(self, blinkState):
    if self.blinkState != blinkState:
      self.blinkState = blinkState
      self.changedSinceRefresh = True

  def setType(self, signalType):
    if self.trackType != signalType:
      self.trackType = signalType
      self.changedSinceRefresh = True
      
  def draw(self, dc):
    dc.SetBrush(wx.Brush('#000'))
    dc.SetPen(wx.Pen("#000"))
    dc.DrawRectangle(self.x, self.y, self.cellSize, self.cellSize)

    if self.blinky and self.blinkState:
      color = TrackCellColors.getColor('signal_blinkoff')
    else:
      color = self.color
      
    dc.SetPen(wx.Pen(color, width=2))
    dc.SetBrush(wx.Brush(color))

    if self.trackType == TrackCellType.SIG_SINGLE_RIGHT:
      dc.DrawCircle(self.x + self.cellSize - 3, self.y + self.cellSize//2, 3)
      dc.SetBrush(wx.Brush('#000'))
      dc.DrawLine(self.x, self.y + self.cellSize//2, self.x + self.cellSize - 7, self.y + self.cellSize//2)
      dc.DrawLine(self.x, self.y + self.cellSize//2 - 4, self.x, self.y + self.cellSize//2 + 4)

    elif self.trackType == TrackCellType.SIG_DOUBLE_RIGHT:
      dc.DrawCircle(self.x + self.cellSize - 3, self.y + self.cellSize//2, 3)
      dc.DrawCircle(self.x + self.cellSize - 9, self.y + self.cellSize//2, 3)
      dc.SetBrush(wx.Brush('#000'))
      dc.DrawLine(self.x, self.y + self.cellSize//2, self.x + self.cellSize - 7, self.y + self.cellSize//2)
      dc.DrawLine(self.x, self.y + self.cellSize//2 - 4, self.x, self.y + self.cellSize//2 + 4)

    elif self.trackType == TrackCellType.SIG_SINGLE_LEFT:
      dc.DrawCircle(self.x + 3, self.y + self.cellSize//2, 3)
      dc.SetBrush(wx.Brush('#000'))
      dc.DrawLine(self.x + self.cellSize-1, self.y + self.cellSize//2, self.x + 6, self.y + self.cellSize//2)
      dc.DrawLine(self.x + self.cellSize-1, self.y + self.cellSize//2 - 4, self.x + self.cellSize-1, self.y + self.cellSize//2 + 4)

    elif self.trackType == TrackCellType.SIG_DOUBLE_LEFT:
      dc.DrawCircle(self.x + 3, self.y + self.cellSize//2, 3)
      dc.DrawCircle(self.x + 9, self.y + self.cellSize//2, 3)
      dc.SetBrush(wx.Brush('#000'))
      dc.DrawLine(self.x + self.cellSize-1, self.y + self.cellSize//2, self.x + 6, self.y + self.cellSize//2)
      dc.DrawLine(self.x + self.cellSize-1, self.y + self.cellSize//2 - 4, self.x + self.cellSize-1, self.y + self.cellSize//2 + 4)

    self.changedSinceRefresh = False      
      
class SwitchCell(TrackCell):
  def __init__(self):
    super().__init__()
    self.switchState = 0
    self.switchStatusColor = TrackCellColors.getColor('switch_unknown')
    pass

  def setSwitchPosition(self, pos):
    if pos != self.switchState:
      self.changedSinceRefresh = True
      self.switchState = pos

  def getSwitchPosition(self):
    return self.switchState

  def setSwitchStatusColor(self, color):
    if color != self.switchStatusColor:
      self.switchStatusColor = color
      self.changedSinceRefresh = True
      
  def draw(self, dc):
    dc.SetBrush(wx.Brush('#000'))
#    dc.SetPen(wx.Pen("#E1FCFF", width=1))
    dc.SetPen(wx.Pen("#000"))
    dc.DrawRectangle(self.x, self.y, self.cellSize, self.cellSize)

    dc.SetPen(wx.Pen(self.switchStatusColor, width=1))
    dc.DrawRectangle(self.x+2, self.y+2, self.cellSize-4, self.cellSize-4)
    dc.SetPen(wx.Pen(self.color, width=2))
    
    if self.trackType == TrackCellType.SWITCH_RIGHT_DOWN:
      if self.switchState != 0:
        dc.DrawLine(self.x, self.y+(self.cellSize//2 - 1), self.x+(self.cellSize//2), self.y+(self.cellSize/2 - 1))
        dc.DrawLine(self.x+(self.cellSize//2), self.y+(self.cellSize/2 - 1), self.x+(self.cellSize - 1), self.y+(self.cellSize - 1))
      else:
        dc.DrawLine(self.x, self.y + (self.cellSize/2 - 1), self.x+self.cellSize-1, self.y + (self.cellSize/2 - 1))

    elif self.trackType == TrackCellType.SWITCH_RIGHT_UP:
      if self.switchState != 0:
        dc.DrawLine(self.x, self.y+(self.cellSize//2 - 1), self.x+(self.cellSize//2), self.y+(self.cellSize//2 - 1))
        dc.DrawLine(self.x+(self.cellSize//2), self.y+(self.cellSize//2 - 1), self.x + (self.cellSize - 1), self.y)
      else:
        dc.DrawLine(self.x, self.y + (self.cellSize/2 - 1), self.x+self.cellSize-1, self.y + (self.cellSize/2 - 1))

    elif self.trackType == TrackCellType.SWITCH_LEFT_DOWN:
      if self.switchState != 0:
        dc.DrawLine(self.x + (self.cellSize - 1), self.y+(self.cellSize//2 - 1), self.x+(self.cellSize//2), self.y+(self.cellSize//2 - 1))
        dc.DrawLine(self.x+(self.cellSize/2 - 1), self.y+(self.cellSize//2 - 1), self.x, self.y+(self.cellSize - 1))
      else:
        dc.DrawLine(self.x, self.y + (self.cellSize/2 - 1), self.x+self.cellSize-1, self.y + (self.cellSize/2 - 1))

    elif self.trackType == TrackCellType.SWITCH_LEFT_UP:
      if self.switchState != 0:
        dc.DrawLine(self.x + (self.cellSize - 1), self.y+(self.cellSize//2 - 1), self.x+(self.cellSize//2), self.y+(self.cellSize/2 - 1))
        dc.DrawLine(self.x+(self.cellSize//2), self.y+(self.cellSize//2 - 1), self.x, self.y)
      else:
        dc.DrawLine(self.x, self.y + (self.cellSize/2 - 1), self.x+self.cellSize-1, self.y + (self.cellSize/2 - 1))

    self.changedSinceRefresh = False
