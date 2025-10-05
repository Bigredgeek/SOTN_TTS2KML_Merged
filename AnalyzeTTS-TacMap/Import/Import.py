import json
import os
import uuid

with open('templates.json') as templateFile:
    templateStr = templateFile.read()

def getTemplate(name):
    templates = json.loads(templateStr)
    template = templates[name]
    template['GUID'] = str(uuid.uuid4())[:6]
    return template

def createCardEntry(data):
    card = getTemplate('cardEntry')
    card['FaceURL'] = data['front_png_url']
    card['BackURL'] = data['back_png_url']
    return dict(card)

def createCard(cardID, cardEntry):
    card= getTemplate('card')
    card['CardID'] = int(cardID)*101
    card['CustomDeck'] = {cardID:cardEntry}
    return card
    
def createDeck(data, name):
    deck = getTemplate('deck')
    deck['CustomDeck'] = {str(i+1):createCardEntry(data[cardEntry]) for i,cardEntry in enumerate(data)}
    deck['DeckIDs'] = [int(k) * 101 for k in deck['CustomDeck'].keys()]
    deck['Nickname'] = name
    deck['ContainedObjects'] = [createCard(cardId, entry) for cardId, entry in deck['CustomDeck'].items()]
    return deck
    
def createTile(data, name, tags):
    frontUrl = data.get('front_png_url')
    if frontUrl is None:
        return None;

    tile = getTemplate('tile')
    tile['Tags'] = tags
    tile['CustomImage']['ImageURL'] = frontUrl
    if data['back_png_url'] == "":
        tile['CustomImage']['ImageSecondaryURL'] = tile['CustomImage']['ImageURL']
    else:
        tile['CustomImage']['ImageSecondaryURL'] = data['back_png_url']
    tile['Nickname'] = name
    return tile
    
def createCounterBox(data, name, tags):
    bag = getTemplate('bag')
    bag['Nickname'] = name
    bag['Tags'] = tags
    for objectName, subObjects in data.items():
        objectTags =[*tags, objectName]
        groupObject = createObject(subObjects, objectName, objectTags)
        bag['ContainedObjects'].append(groupObject)
    return bag

def createObject(data, name, tags):
    tile = createTile(data, name, tags)
    if tile is not None:
        return tile
    else:
        return createCounterBox(data, name, tags)
    

with open('Red_Strike_V1_2.vmod_factions.json') as dataFile:
    factionData =json.loads(dataFile.read())
    
with open('Red_Strike_V1_2.vmod_cards.json') as dataFile:
    cardData =json.loads(dataFile.read())

with open('Red_Strike_V1_2.vmod_markers.json') as dataFile:
    markersData =json.loads(dataFile.read())
    
counterBag = getTemplate('bag')
counterBag['Nickname'] = 'Generated Counters'
counterBag['ContainedObjects'] = [
    createCounterBox(factionData['NATO Units'],'NATO',['NATO']), 
    createCounterBox(factionData['WP Units'],'Pact',['WP']),
    createCounterBox(markersData,'Markers',['Marker']),
    createDeck(cardData['NATO Cards'],'NATO Cards'),
    createDeck(cardData['WP Cards'],'Pact Cards')
    ]

ttsSave = getTemplate('ttsSave')
ttsSave['ObjectStates'] = [counterBag]
with open('RS89_Tokens.json','w') as counterFile:
    json.dump(ttsSave,counterFile, indent=4)
    