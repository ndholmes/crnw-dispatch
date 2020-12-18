import re
import json
import datetime

class MRBusPacket:
  def __init__(self, dest=0, src=0, cmd=0, data=0):
    self.dest=int(str(dest), 0)
    self.src=int(str(src), 0)
    self.cmd=int(str(cmd), 0)
    self.data = []
    for d in data:
      self.data.append(int(str(d), 0))

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

  def toJSON(self):
    updateTime = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc).isoformat()
    pktinfo = { 'type': 'pkt', 'src': self.src, 'dst': self.dest, 'cmd': self.cmd, 'data':self.data, 'time': updateTime }
#    mosquitto_pub -h crnw.drgw.net -t 'crnw/send' -m "{\"cmd\": \"0x43\", \"data\": [\"0x02\", \"0x44\", \"0x57\"], \"dst\": \"0x37\", \"src\": 254, \"time\": \"2020-12-17T05:02:08.280321+00:00\", \"type\": \"pkt\"}"
    return json.dumps(pktinfo, sort_keys=True)

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
  def testPacket(self, pkt, debug=False):
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
