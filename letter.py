# letter.py
#
# How to communicate with worker ?

import socket
import json

import typing
from typing import *

from datetime import datetime

def newTaskLetterValidity(letter: 'Letter') -> bool:
    isHValid = letter.getHeader('ident') != "" and letter.getHeader('tid') != ""
    isCValid = letter.getContent('sn') != "" and \
               letter.getContent('vsn') != ""

    return isHValid and isCValid

def responseLetterValidity(letter: 'Letter') -> bool:
    isHValid = letter.getHeader('ident') != "" and letter.getHeader('tid') != ""
    isCValid = letter.getContent('state') != ""

    return isHValid and isCValid

def propertyLetterValidity(letter: 'Letter') -> bool:
    isHValid = letter.getHeader('ident') != ""
    isCValid = letter.getContent('MAX') != "" and letter.getContent('PROC') != ""

    return isHValid and isCValid

def binaryLetterValidity(letter: 'Letter') -> bool:
    isHValid = letter.getHeader('tid') != ""
    isCValid = letter.getContent('bytes') != ""

    return isHValid and isCValid

def logLetterValidity(letter: 'Letter') -> bool:
    isHValid = letter.getHeader('logId') != ""
    isCValid = letter.getContent('logMsg') != ""

    return isHValid and isCValid

def logRegisterLetterValidity(letter: 'Letter') -> bool:
    isHValid = letter.getHeader('logId') != ""

    return isHValid

class Letter:

    # Format of NewTask letter
    # Type    : 'new'
    # header  : '{"ident":"...", "tid":"..."}'
    # content : '{"sn":"...", "vsn":"...", "datetime":"..."}'
    NewTask = 'new'

    # Format of TaskCancel letter
    # Type    : 'cancel'
    # header  : '{"ident":"...", "tid":"..."}'
    # content : '{}'
    TaskCancel = 'cancel'

    # Format of Response letter
    # Type    : 'response'
    # header  : '{"ident":"...", "tid":"..."}
    # content : '{"state":"..."}
    Response = 'response'

    RESPONSE_STATE_PREPARE = "0"
    RESPONSE_STATE_IN_PROC = "1"
    RESPONSE_STATE_FINISHED = "2"
    RESPONSE_STATE_FAILURE = "3"

    # Format of PrpertyNotify letter
    # Type    : 'notify'
    # header  : '{"ident":"..."}'
    # content : '{"MAX":"...", "PROC":"..."}'
    PropertyNotify = 'notify'

    # Format of binary letter in a stream
    # | Type (2Bytes) 00001 :: Int | Length (4Bytes) :: Int | Ext (10 Bytes) | TaskId (64Bytes) :: String | Content |
    # Format of BinaryFile letter
    # Type    : 'binary'
    # header  : '{"tid":"..."}
    # content : "{"bytes":b"..."}"
    BinaryFile = 'binary'

    # Format of log letter
    # Type : 'log'
    # header : '{"logId":"..."}'
    # content: '{"logMsg":"..."}'
    Log = 'log'

    # Format of LogRegister letter
    # Type    : 'LogRegister'
    # header  : '{"logId"}'
    # content : "{}"
    LogRegister = 'logRegister'

    BINARY_HEADER_LEN = 80
    BINARY_MIN_HEADER_LEN = 6

    MAX_LEN = 512

    format = '{"type":"%s", "header":%s, "content":%s}'

    def __init__(self, type_: str,
                 header: Dict[str, str] = {},
                 content: Dict[str, Union[str, bytes]] = {}) -> None:

        self.type_ = type_

        # header field is a dictionary
        self.header = header

        # content field is a dictionary
        self.content = content

        #if not self.validity():
        #    print(self.type_ + str(self.header) + str(self.content))

    # Generate a json string
    def toString(self) -> str:
        # length of content after length
        headerStr = str(self.header).replace("'", "\"")
        contentStr = str(self.content).replace("'", "\"")
        return Letter.format % (self.type_, headerStr, contentStr)

    def toJson(self) -> Dict:
        jsonStr = self.toString()
        return json.loads(jsonStr)

    def toBytesWithLength(self) -> bytes:
        str = self.toString()
        bStr = str.encode()

        return len(bStr).to_bytes(2, "big") + bStr

    @staticmethod
    def json2Letter(s: str) -> 'Letter':
        dict_ = None

        begin = s.find('{')
        dict_ = json.loads(s[begin:])

        return Letter(dict_['type'], dict_['header'], dict_['content'])

    def typeOfLetter(self) -> str:
        return self.type_

    def getHeader(self, key: str) -> str:
        if key in self.header:
            return self.header[key]
        else:
            return ""

    def addToHeader(self, key: str, value: str) -> None:
        self.header[key] = value

    def addToContent(self, key: str, value: str) -> None:
        self.content[key] = value

    def getContent(self, key: str) -> Union[bytes, str]:
        if key in self.content:
            return self.content[key]
        else:
            return ""

    # If a letter is received completely return 0 otherwise return the remaining bytes
    @staticmethod
    def letterBytesRemain(s: bytes) -> int:
        # Need at least BINARY_MIN_HEADER_LEN bytes to parse
        if len(s) < Letter.BINARY_MIN_HEADER_LEN:
            return Letter.MAX_LEN

        if int.from_bytes(s[:2], "big") == 1:
            length = int.from_bytes(s[2:6], "big")
            return length - (len(s) - Letter.BINARY_HEADER_LEN)
        else:
            length = int.from_bytes(s[:2], "big")
            return length - (len(s) - 2)

    @staticmethod
    def parse(s : bytes) -> Optional['Letter']:
        # Need at least BINARY_MIN_HEADER_LEN bytes to parse
        if len(s) < Letter.BINARY_MIN_HEADER_LEN:
            return None

        # To check that is BinaryFile type or another
        if int.from_bytes(s[:2], "big") == 1:
            return BinaryLetter.parse(s)
        else:
            return Letter.__parse(s)

    @staticmethod
    def __parse(s: bytes) -> Optional['Letter']:
        letter = s[2:].decode()
        dict_ = json.loads(letter)

        type_ = dict_['type']

        return parseMethods[type_].parse(s)

    def validity(self) -> bool:
        type = self.typeOfLetter()
        return validityMethods[type](self)

    # PropertyNotify letter interface
    def propNotify_MAX(self) -> int:
        return int(self.content['MAX'])
    def propNotify_PROC(self) -> int:
        return int(self.content['PROC'])
    def propNotify_IDENT(self) -> str:
        return self.header['ident']

def bytesDivide(s:bytes) -> Tuple:
    letter = s[2:].decode()
    dict_ = json.loads(letter)

    type_ = dict_['type']
    header = dict_['header']
    content = dict_['content']

    return (type_, header, content)

class NewLetter(Letter):

    def __init__(self, ident:str, tid:str, sn:str, vsn:str, datetime:str) -> None:
        Letter.__init__(
            self,
            Letter.NewTask,
            {"ident":ident, "tid":tid},
            {"sn":sn, "vsn":vsn, "datetime":datetime}
        )

    @staticmethod
    def parse(s:bytes) -> Optional['NewLetter']:

        (type_, header, content) = bytesDivide(s)

        if type_ != Letter.NewTask:
            return None

        return NewLetter(
            ident = header['ident'],
            tid = header['tid'],
            sn = content['sn'],
            vsn = content['vsn'],
            datetime = content['datetime'])

class ResponseLetter(Letter):

    def __init__(self, ident:str, tid:str, state:str) -> None:
        Letter.__init__(
            self,
            Letter.Response,
            {"ident":ident, "tid":tid},
            {"state":state}
        )

    @staticmethod
    def parse(s:bytes) -> Optional['ResponseLetter']:
        (type_, header, content) = bytesDivide(s)

        if type_ != Letter.Response:
            return None

        return ResponseLetter(
            ident = header['ident'],
            tid = header['tid'],
            state = content['state']
        )

class PropLetter(Letter):

    def __init__(self, ident:str, max:str, proc:str) -> None:
        Letter.__init__(
            self,
            Letter.PropertyNotify,
            {"ident":ident},
            {"MAX":max, "PROC":proc}
        )

    @staticmethod
    def parse(s:bytes) -> Optional['PropLetter']:
        (type_, header, content) = bytesDivide(s)

        if type_ != Letter.PropertyNotify:
            return None

        return PropLetter(
            ident = header['ident'],
            max = content['MAX'],
            proc = content['PROC']
        )

class BinaryLetter(Letter):

    def __init__(self, tid:str, bStr:bytes, extension:str = "") -> None:
        Letter.__init__(
            self,
            Letter.BinaryFile,
            {"tid":tid, "extension":extension},
            {"bytes":bStr}
        )

    @staticmethod
    def parse(s:bytes) -> Optional['BinaryLetter']:
        extension = s[6:16].decode().replace(" ", "")
        tid = s[16:70].decode().replace(" ", "")
        content = s[70:]

        return BinaryLetter(tid, content, extension)

    def toBytesWithLength(self) -> bytes:

        bStr = self.binaryPack()

        if bStr is None:
            return b''

        return bStr

    def binaryPack(self) -> Optional[bytes]:
        tid = self.getHeader('tid')
        extension = self.getHeader('extension')
        content = self.getContent("bytes")

        if type(content) is str:
            return None

        tid_field = b"".join([" ".encode() for x in range(64 - len(tid))]) + tid.encode()
        ext_field = b"".join([" ".encode() for x in range(10 - len(extension))]) + extension.encode()

        # Safe here content must not str and must a bytes
        packet = (1).to_bytes(2, "big") + (len(content)).to_bytes(4, "big")\
                 + ext_field + tid_field + content # type: ignore

        return packet


class LogLetter(Letter):

    def __init__(self, logId:str, logMsg:str) -> None:
        Letter.__init__(
            self,
            Letter.Log,
            {"logId":logId},
            {"logMsg":logMsg}
        )

    @staticmethod
    def parse(s:bytes) -> Optional['LogLetter']:
        (type_, header, content) = bytesDivide(s)

        if type_ != Letter.Log:
            return None

        return LogLetter(
            logId = header['logId'],
            logMsg = content['logMsg']
        )

class LogRegLetter(Letter):

    def __init__(self, logId:str) -> None:
        Letter.__init__(
            self,
            Letter.LogRegister,
            {"logId":logId},
        )

    @staticmethod
    def parse(s:bytes) -> Optional['LogRegLetter']:
        (type_, header, content) = bytesDivide(s)

        if  type_ != Letter.LogRegister:
            return None

        return LogRegLetter(
            logId = header['logId']
        )

validityMethods = {
    Letter.NewTask        :newTaskLetterValidity,
    Letter.Response       :responseLetterValidity,
    Letter.PropertyNotify :propertyLetterValidity,
    Letter.BinaryFile     :binaryLetterValidity,
    Letter.Log            :logLetterValidity,
    Letter.LogRegister    :logRegisterLetterValidity,
} # type: Dict[str, Callable]

parseMethods = {
    Letter.NewTask        :NewLetter,
    Letter.Response       :ResponseLetter,
    Letter.PropertyNotify :PropLetter,
    Letter.BinaryFile     :BinaryLetter,
    Letter.Log            :LogLetter,
    Letter.LogRegister    :LogRegLetter
} # type: Any
