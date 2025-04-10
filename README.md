# WriterServer
A general python server to write data

pip install the released wheel

then 

```python 
from writerserver import writer
```
on the server
```python 
server = writer.Server(path = "path_to_your_data",ip= "XXX.XXX.XXX.XXX",port = YYYY)
server.start()
```

then start a client
```python
N = number_of_columns_for_your_data
client = writer.Client(N = N,ip= "XXX.XXX.XXX.XXX",port = YYYY,project = project)
client.start()
```
then you can send data

```python
client.write(data)
```
the length of your data should be a multiple of N

the identifying number for your data can be found using

```python
name = client.getName()
```

and the path to your data on the server is given by

```python
path = writer.pather("path_to_your_data"+"/"+project,write.getUUIDPath(name))
```
