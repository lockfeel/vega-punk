# -*- coding: utf-8 -*-

import re
from typing import List, Tuple


class OutputFilter:
    CODE_BLOCK_PATTERN = r'```(\w+)?\n(.*?)```'

    DANGEROUS_COMMANDS = [
        r'rm\s+-[rf]+\s+',
        r'del\s+/[sq]',
        r'dd\s+',
        r'mkfs\s+',
        r'chmod\s+[47][0-7]{3}',
        r'chown\s+',
        r'curl\s+.*\|',
        r'wget\s+.*\|',
        r'\|.*sh',
        r'nc\s+-[lpe]',
        r'nmap\s+',
        r'ping\s+-[cf]',
        r'sudo\s+',
        r'su\s+',
        r'passwd\s+',
        r'useradd\s+',
        r'userdel\s+',
        r'systemctl\s+',
        r'service\s+',
        r'kill\s+-9',
        r'pkill\s+',
        r'killall\s+',
        r'curl\s+http.*\.sh',
        r'wget\s+http.*\.sh',
        r'python\s+-c.*exec',
        r'eval\s*\(',
    ]

    @classmethod
    def extractCommands(cls, text: str) -> List[str]:
        commands = []

        for match in re.finditer(cls.CODE_BLOCK_PATTERN, text, re.DOTALL):
            code = match.group(2).strip()
            if code:
                for line in code.split('\n'):
                    line = line.strip()
                    if line and not line.startswith('#') and not line.startswith('#!'):
                        commands.append(line)

        for line in text.split('\n'):
            line = line.strip()
            if line.startswith('$ ') or line.startswith('> '):
                cmd = line[2:].strip()
                if cmd:
                    commands.append(cmd)

        if not commands:
            text = text.strip()
            dangerousKeywords = ['rm ', 'curl ', 'wget ', 'nmap ', 'nc ', 'sudo ', 'chmod ', 'chown ']
            if any(kw in text.lower() for kw in dangerousKeywords):
                commands.append(text)

        return commands

    @classmethod
    def auditOutput(cls, text: str) -> Tuple[bool, List[str]]:
        commands = cls.extractCommands(text)

        dangerous = []
        for cmd in commands:
            for pattern in cls.DANGEROUS_COMMANDS:
                if re.search(pattern, cmd, re.IGNORECASE):
                    dangerous.append(cmd)
                    break

        return len(dangerous) > 0, dangerous

    @classmethod
    def filterOutput(cls, text: str) -> str:
        hasDangerous, commands = cls.auditOutput(text)

        if hasDangerous:
            warning = f"\n\n⚠️ **安全提示**: 检测到以下命令，请确认安全后再执行：\n"
            for cmd in commands[:5]:
                warning += f"```\n{cmd}\n```\n"

        return text


if __name__ == '__main__':
    testOutputs = [
        """
这是一个清理脚本：
```bash
#!/bin/bash
rm -rf /tmp/*
```
        """,
        """
你可以运行这个命令：
```python
import os
os.system('ls -la')
```
        """,
        """
你好！有什么可以帮助你的吗？
        """
    ]

    print("🛡️ 输出过滤测试\n")
    for i, text in enumerate(testOutputs, 1):
        hasDangerous, commands = OutputFilter.auditOutput(text)
        print(f"测试 {i}: {'⚠️ 发现危险命令' if hasDangerous else '✅ 安全'}")
        if commands:
            for cmd in commands:
                print(f"  命令: {cmd[:50]}...")
        print()
