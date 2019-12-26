# letter.py
#
# How to communicate with worker ?

import socket
import json

import typing
from typing import Dict

class Letter:

    # Format of NewTask letter
    # Type    : 'new'
    # header  : '{"ident":"...", "tid":"..."}'
    # content : '{"sn":"...", "vsn":"..."}'
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

    # Format of PrpertyNotify letter
    # Type    : 'notify'
    # header  : '{"ident":"..."}'
    # content : '{"MAX":"...", "PROC":"..."}'
    PropertyNotify = 'notify'

    # Format of binary letter in a stream
    # | Type (2Bytes) 00001 :: Int | Length (4Bytes) :: Int | TaskId (64Bytes) :: String | Content |
    # Format of BinaryFile letter
    # Type    : 'binary'
    # header  : '{"tid":"..."}
    # content : "{"bytes":b"..."}"
    BinaryFile = 'binary'

    BINARY_HEADER_LEN = 70
    BINARY_MIN_HEADER_LEN = 6

    MAX_LEN = 512

    format = '{"type":"%s", "header":%s, "content":%s}'

    def __init__(self, type_: str,
                 header: Dict[str, str] = {},
                 content: Dict[str, str] = {}) -> None:

        # Type of letter:
        # (1) NewTask
        # (2) TaskCancel
        # (3) Response
        self.type_ = type_

        # header field is a dictionary
        self.header = header

        # content field is a dictionary
        self.content = content

    # Generate a json string
    def toString(self) -> str:
        # length of content after length
        headerStr = str(self.header).replace("'", "\"")
        contentStr = str(self.content).replace("'", "\"")
        return Letter.format % (self.type_, headerStr, contentStr)

    def toJson(self) -> Dict:
        jsonStr = self.toString()
        return json.loads(jsonStr)

    def toBytesWithLength(self):
        str = self.toString()
        bStr = str.encode()

        return len(bStr).to_bytes(2, "big") + bStr

    def binaryPack(self):
        if self.typeOfLetter() != Letter.BinaryFile:
            return None

        tid = self.getHeader("tid")
        content = self.getContent("bytes")

        tid_field = b"".join([" ".encode() for x in range(64 - len(tid))]) + tid.encode()
        packet = (1).to_bytes(2, "big")\
                 + (len(content)).to_bytes(4, "big")\
                 + tid_field\
                 + content
        return packet

    @staticmethod
    def json2Letter(s: str):
        dict_ = None

        begin = s.find('{')
        dict_ = json.loads(s[begin:])

        return Letter(dict_['type'], dict_['header'], dict_['content'])

    def typeOfLetter(self) -> str:
        return self.type_

    def getHeader(self, key: str) -> str:
        return self.header[key]

    def addToHeader(self, key: str, value: str) -> None:
        self.header[key] = value

    def addToContent(self, key: str, value: str) -> None:
        self.content[key] = value

    def getContent(self, key: str) -> str:
        return self.content[key]

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
    def parse(s : typing.ByteString):
        # Need at least BINARY_MIN_HEADER_LEN bytes to parse
        if len(s) < Letter.BINARY_MIN_HEADER_LEN:
            return None

        # To check that is BinaryFile type or another
        if int.from_bytes(s[:2], "big") == 1:
            return Letter.__parse_binary(s)
        else:
            return Letter.__parse(s)

    @staticmethod
    def __parse_binary(s):
        tid = s[6:70].decode().replace(" ", "")
        content = s[70:]

        return Letter(Letter.BinaryFile, {"tid":tid}, {"content":content})

    @staticmethod
    def __parse(s):
        letter = s[2:].decode()
        dict_ = json.loads(letter)

        return Letter(dict_['type'], dict_['header'], dict_['content'])


    # PropertyNotify letter interface
    def propNotify_MAX(self) -> int:
        return int(self.content['MAX'])
    def propNotify_PROC(self) -> int:
        return int(self.content['PROC'])
    def propNotify_IDENT(self) -> str:
        return self.header['ident']
