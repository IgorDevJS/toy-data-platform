import subprocess, datetime, sys, csv, io, math, json
CUBE = ["docker","run","--rm","--network","platform-net","-e","PGPASSWORD=cubecubecube","postgres:16",
        "psql","-h","cube","-p","15432","-U","cube","-d","cube"]
TRINO = ["docker","exec","toy-data-platform-trino-1","trino"]
def ts(): return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
def cube(sql, out):
    r = subprocess.run(CUBE+["-c",sql], capture_output=True, text=True, check=True).stdout
    out.append(f'$ psql -h cube -p 15432 -U cube -d cube -c "{sql}"  ({ts()})\n{r}\n')
    return r
def cube_rows(sql):
    r = subprocess.run(CUBE+["-A","-F","\t","-P","footer=off","-c",sql], capture_output=True, text=True, check=True).stdout
    return list(csv.DictReader(io.StringIO(r), delimiter="\t"))
def trino(sql, out):
    r = subprocess.run(TRINO+["--output-format","ALIGNED","--execute",sql], capture_output=True, text=True, check=True).stdout
    out.append(f'$ trino --execute "{sql}"  ({ts()})\n{r}\n')
    return r
def trino_rows(sql):
    r = subprocess.run(TRINO+["--output-format","TSV_HEADER","--execute",sql], capture_output=True, text=True, check=True).stdout
    return list(csv.DictReader(io.StringIO(r), delimiter="\t"))
