# repadmin-parser

Minimal Python parser for `repadmin ` replication metadata listings. There's no unambiguous (nor context-free) output format for that Microsoft tool, so I developed this small parser to put everything back together into TSV or JSON, or summarise important changes.

## Usage

First, choose a naming context to monitor, and record its current USN into a file (a "cookie"):

```
	repadmin /showchanges <domain controller fqdn> <naming context DN> /cookie:cookie.txt >NUL
	# e.g. repadmin /showchanges localhost DC=lab,DC=local /cookie:cookie.txt >NUL
```

Then, wait for modifications and list them using:

```
	repadmin /showchanges localhost dc=lab,dc=local /cookie:cookie.txt

	Using cookie from file cookie.txt (108 bytes)
	==== SOURCE DSA: localhost ====
	Objects returned: 1
	(0) add CN=My New User,CN=Users,DC=lab,DC=local
	4> objectClass: top; person; organizationalPerson; user
	1> whenCreated: 6/23/2019 8:22:48 AM Pacific Daylight Time
	[...]
	New cookie written to file cookie.txt (108 bytes)
```

You can parse repadmin's output using this script to insert them into a database, easier to query:

```
	repadmin /showchanges localhost dc=lab,dc=local /cookie:cookie.txt >changes.txt
	python3 repadmin_parser.py .\changes.txt --format=tsv --outfile=changes.tsv
	# then, use example_bulk_insert.sql to import changes.tsv into SQL
```

You can also use it to list which users or workstations have changed their password in the last days, e.g. if you're going to have to restore an AD backup and all workstations with an updated password will get desynchronised and lose AD connectivity:

```
	python3 repadmin_parser.py .\changes.txt --format=passwords
	2019-06-21 14:06:48 UTC	CN=WKS-10243,OU=Workstations,DC=lab,DC=local
	2019-06-21 14:06:21 UTC	CN=S-MSSQL-01,OU=EastCoast,OU=Servers,DC=lab,DC=local
	2019-06-21 14:06:59 UTC	CN=U02384,OU=Users,OU=Accounts,DC=lab,DC=local
	2019-06-21 13:06:54 UTC	CN=U28440,OU=Users,OU=Accounts,DC=lab,DC=local
	2019-06-21 14:06:09 UTC	CN=WKS-18274,OU=France,OU=Workstations,DC=lab,DC=local
	2019-06-21 13:06:05 UTC	CN=adm-r-21,OU=Red-Admins,OU=Accounts,DC=lab,DC=local
	2019-06-21 14:06:06 UTC	CN=U02847,OU=Users,OU=Accounts,DC=lab,DC=local
	2019-06-21 14:06:54 UTC	CN=U92734,OU=Users,OU=Accounts,DC=lab,DC=local
	2019-06-21 14:06:14 UTC	CN=WKS-10238,OU=Workstations,DC=lab,DC=local
	2019-06-21 15:06:06 UTC	CN=U83744,OU=Users,OU=Accounts,DC=lab,DC=local
```

