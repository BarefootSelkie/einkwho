#!/usr/bin/env python3

import time
import yaml
import requests
import logging
import argparse
from PIL import Image, ImageFont, ImageDraw
from pktools import pktools
from inky.auto import auto

# Arguments and logging
parser = argparse.ArgumentParser()
parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging")
args = parser.parse_args()

if args.verbose:
  logging.basicConfig(format="%(asctime)s : %(message)s", filename="log-eink-whome.log", encoding='utf-8', level=logging.DEBUG)
else:
  logging.basicConfig(format="%(asctime)s : %(message)s", filename="log-eink-whome.log", encoding='utf-8', level=logging.WARN)

# Load settings
try:
  with open("./config-eink-whome.yaml", "r") as read_file:
    config = yaml.safe_load(read_file)
except:
  logging.critical("Settings file missing")
  exit()

# Check that the library is up to date enough
try:
  inky_display = auto(ask_user=True, verbose=True)
except TypeError:
  raise TypeError("You need to update the Inky library to >= v1.1.0")

# Set the fonts and sizes
bigFont = ImageFont.truetype("./LeagueSpartan-Medium.ttf", int(44))
smallFont = ImageFont.truetype("./LeagueSpartan-Medium.ttf", int(24))
symbolFont = ImageFont.truetype("./NotoSansSymbols2-Regular.ttf", int(32))

# Create a variable that holds what will be drawn onto the screen
img  = Image.new( mode = "P", size = inky_display.resolution )

# Create a variable that allows access to the drawing functions
draw = ImageDraw.Draw(img)

state = { "lastSwitch": {"timestamp": "" }}

# Returns the member that should be displayed on the display
def getFronter():
  global state
  if len(state["lastSwitch"]["members"]) == 0:
    return None
  id = state["lastSwitch"]["members"][0]
  member, private = pktools.getMember(id, state["pkMembers"])
  if private:
    member, private = pktools.getMember("ogymz", state["pkMembers"])
  return member

def getFirstFronter(currentFronters):
  display = {}

  if len(state["lastSwitch"]["members"]) == 0:
    display["name"] = "zzz"
  else:
    firstFronter = currentFronters["members"][0]
    
    if firstFronter["visible"]:
      display["name"] = firstFronter["name"]
      if firstFronter["memberPronouns"] is not None:
        display["pronouns"] = firstFronter["pronouns"]
    else:
      display["name"] = currentFronters["system"]["name"]
      if currentFronters["system"]["pronouns"] is not None:
        display["pronouns"] = currentFronters["system"]["pronouns"]
        
    if firstFronter["cardsName"] is not None:
      display["cardsName"] = firstFronter["cardsName"]
  
  return display

def fetchState():
  global state
  try:
    serverUrl = "http://" + str(config["server"]) + ":" + str(config["port"])
    lastSwitch = requests.get(serverUrl + "/lastSwitch.json").json()
    if state["lastSwitch"]["timestamp"] != lastSwitch["timestamp"]:
      state["pkMembers"] = requests.get(serverUrl + "/pkMembers.json").json()
      state["memberList"] = requests.get(serverUrl + "/memberList.json").json()
      state["lastSwitch"] = lastSwitch
      return True
  except Exception as e:
    logging.warning("Cannot fetch current front ( fetchState() )")
    logging.warning(e)
  return False


# Create and image to draw on the screen
def drawScreen(fronter):
  # Draw a white background on the display
  draw.rectangle(((0, 0), inky_display.resolution), inky_display.WHITE, None, 0)
  
  if fronter is not None:  
    # Draw text on the display
    draw.text((inky_display.resolution[0] / 2, 32), fronter["name"], inky_display.BLACK, font=bigFont, anchor="mm")
    if fronter["pronouns"] is not None:
      draw.text((8, 86), fronter["pronouns"], inky_display.BLACK, font=smallFont, anchor="lm")

    # Draw the card suit if one exists
    for member in state["memberList"]:
      if member["memberId"] == fronter["id"]:
        cardSuit = member["cardsName"][:1]
        if cardSuit in ["♠", "♣"]:
          cardColour = inky_display.BLACK
        else:
          cardColour = inky_display.RED
        draw.text((inky_display.resolution[0] - 6, 92), cardSuit, cardColour, font=symbolFont, anchor="rm")

  # Rotate the image as the pi has power cables coming out the usb ports so is mounted gpio connector down
  return(img.rotate(180))


# Check the data is up to date on first run
fetchState()
inky_display.set_image(drawScreen(getFronter()))
inky_display.show()

### Main code loop ###
minutePast = 0

while True:
  # Don't do anything if the minute hasn't changed
  if minutePast != time.localtime()[4]:
    minutePast = time.localtime()[4]

    # If the minute is divisible by updateInterval check for new fronters
    # this is for rate limiting and not hitting the pluralkit api too hard
    updateInterval = 1
    if ( time.localtime()[4] % updateInterval ) == 0:
      updateNeeded = fetchState()

      # If pullPeriodic returns true update the screen and unset updateNeeded
      if updateNeeded:
        inky_display.set_image(drawScreen(getFronter()))
        inky_display.show()
        updateNeeded = False

  # do nothing for a while
  time.sleep(5)
