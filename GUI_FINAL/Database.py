import sqlite3

def createTable():
    connection = sqlite3.connect('login.db')



    connection.execute("INSERT INTO USERS VALUES(?,?,?)",('carlos','15','carlos'))

    connection.commit()

    result = connection.execute("SELECT * FROM USERS")
    
    for data in result:
        print("Username : ",data[0])
        print("Privilegio : ",data[1])
        print("Password :",data[2])

    connection.close()

createTable()
        
    
