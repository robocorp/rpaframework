*** Settings ***
Library    RPA.Crypto

*** Tasks ***
Generate and use key
    ${key}=    Generate key
    Should not be empty    ${key}
    Use encryption key     ${key}

Hash string defaults
    ${hash}=    Hash string    avalue
    Should be equal    ${hash}    eNOTzEOqI0k2ijVhEmKow1YPFGo=

Hash string change method
    ${hash}=    Hash string    avalue    MD5
    Should be equal    ${hash}    3ObaKiohbtSuG4Q8+kIKTg==

Encrypt string
    ${key}=    Generate key
    Use encryption key    ${key}
    ${enc}=    Encrypt string    Something very important here
    Log    ${enc}
    ${dec}=    Decrypt string    ${enc}
    Should be equal    ${dec}    Something very important here
