import pymongo

client = pymongo.MongoClient(
    "mongodb+srv://yhali:215625328@cluster0.jfedfhb.mongodb.net/?retryWrites=true&w=majority")
db = client.test
SECRET_KEY = "qwertyuiolkjhgfdsazxcvbnm"
