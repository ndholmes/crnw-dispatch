import re

class MRBusBit:
  def __init__(self, pattern="", initialState = False):
    self.src = 0
    self.cmd = 0
    self.byte = 0
    self.bit = 0
    self.state = initialState
    if pattern is not "":
      self.fromPattern(pattern)

  # Changes the internal bit state if the packet matches
  # Returns true if this packet applied to us and changed our state
  def testPacket(self, pkt):
    if self.src == 0:
      return False

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
