siteTypes = ['Unstable Wormhole', 'Anomaly', 'Ore Site', 'Relic Site', 'Data Site', 'Gas Site', 'Cosmic Signature']

present = []
findnew = []
notfound = []

for line in paste.split('\n'):
# {
    newP = PasteData(p_system=system)
    found = False
    for section in line.split('\t'):
    # {
        if section is None:
            continue
        elif 'AU' in section:
            continue
        elif '%' in section:
            continue
        elif 'wormhole' in section.lower():
            newP.isSite = False
        elif section == 'Cosmic Signature':
            continue
        elif re.match(r'^[a-zA-Z]{3}-\d{1,3}$', section):
        # {
            section = section.upper()
            if isSite(section[:3]):
                site = getSite(section[:3])
                if site.where == system:
                    notfound.remove(site)
                    found = True
                    present.append(site)
            elif isWormhole(section[:3]):
                wormhole = getWormhole(section[:3])
                if wormhole.start == system:
                    notfound.remove(wormhole)
                    found = True
                    present.append(wormhole)
            if not found:
                newP.scanid = section[:3]
        # }
        elif section in siteTypes:
            newP.type = section
        else:
            newP.name = section
    # }
    if not found:
        findnew.append(newP)
# }