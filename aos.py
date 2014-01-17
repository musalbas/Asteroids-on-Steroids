#!/usr/bin/env python

# Define functions
def calcTheoreticalPos(startTime, movePos, velocity):
    # Calculate the co-ordinates an object should be at based on the time, moving direction and velocity
    m = (ticksSecs - startTime) * velocity
    return (movePos[0] * m, movePos[1] * m)

def objHasHitTarget(target, startRect, curRect, angle):
    # Determine if a moving object has passed a target
    angle = math.degrees(angle)
    if (
        # first quadrant
        (-90 < angle < 0 and startRect.bottomleft[0] < target[0] <= curRect.topright[0] and startRect.bottomleft[1] > target[1] >= curRect.topright[1])
        # second quadrant
        or (0 < angle < 90 and startRect.bottomright[0] > target[0] >= curRect.topleft[0] and startRect.bottomright[1] > target[1] >= curRect.topleft[1])
        # third quadrant
        or (90 < angle < 180 and startRect.topright[0] > target[0] >= curRect.bottomleft[0] and startRect.topright[1] < target[1] <= curRect.bottomleft[1])
        # fourth quadrant
        or (-180 < angle < -90 and startRect.topleft[0] < target[0] <= curRect.bottomright[0] and startRect.topleft[1] < target[1] <= curRect.bottomright[1])
    ):
        return 1

def launchMegaBullet():
    # Launch mega bullet
    angleIncrement = math.radians(360.0 / (args.megaBulletNum + 1))
    for i in range(args.megaBulletNum):
        bullet(angle = angleIncrement * i, travelRange = args.megaBulletRange)

def clrTermLine(flushNow = 0):
    # Clear/blank the current terminal line
    # Assuming that the terminal width is at least 79 characters (it's usually at least 80)
    # TODO: Retrieve terminal width programatically
    print ' ' * 79 + '\r',
    if flushNow == 1:
        sys.stdout.flush()

def updTermLine(string):
    # Update the current terminal line
    clrTermLine()
    print string + '\r',
    sys.stdout.flush()

def importMods(mods):
    # Try to dynamically import modules, ask user to install missing modules
    # Importing large modules can be slow, so it wouldn't hurt to print the progress
    # This is probably an overkill for importing modules
    loadedMods = 0
    missingMods = [[], []]
    extraMissingMods = []
    for mod in mods:
        if mod == 0:
            continue
        try:
            updTermLine('Loading modules (' + str(round(float(loadedMods) / (len(mods) - mods.count(0)) * 100, 2)) + '%)' + (': ' + mod[2] if len(mod) >= 3 else '...'))
            if type(mod) == str:
                mod = (mod, 0)
            globals()[mod[0]] = __import__(mod[0], globals(), locals(), (mod[0] if len(mod) >= 2 and mod[1] != 1 else 0), -1)
            if mod[1] == 1: # If the fromlist is *
                modNameComponents = mod[0].split('.')
                if len(modNameComponents) == 2:
                    curMod = getattr(globals()[modNameComponents[0]], modNameComponents[1])
                else:
                    curMod = globals()[mod[0]]
                for attr in dir(curMod):
                    if attr[0] != '_':
                        globals()[attr] = getattr(curMod, attr)
        except ImportError:
            if len(mod) >= 4:
                missingMods[0].append(mod[2])
                missingMods[1].append(mod[3])
            else:
                # (This shouldn't happen/there shouldn't be a need to issue a warning, unless there is something wrong with the Python installation)
                extraMissingMods.append(mod[0])
        loadedMods += 1
    updTermLine('Loading modules (100%)')
    if missingMods != [[], []]:
        clrTermLine()
        print 'Error: Unable to import module' + ('' if len(missingMods[0]) == 1 else 's')
        print
        print 'Missing module' + ('' if len(missingMods[0]) == 1 else 's') + ':'
        print ', '.join(missingMods[0])
        print
        print 'You may install ' + ('the' if len(missingMods[0]) == 1 else 'these') + ' module' + ('' if len(missingMods[0]) == 1 else 's') + ' (on Raspbian/Debian-like distros) by running:'
        print '\'sudo aptitude install ' + ' '.join(missingMods[1]) + '\''
        quit()
    elif extraMissingMods != []:
        clrTermLine()
        print 'Error: Unable to import module' + ('' if len(extraMissingMods) == 1 else 's') + ': ' + ', '.join(extraMissingMods)
        quit()

def grabScreen():
    # Return a shot of the current screen as a PIL image
    desk = gtk.gdk.get_default_root_window()
    deskSz = desk.get_size()
    img = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, 0, 8, deskSz[0], deskSz[1])
    img = img.get_from_drawable(desk, desk.get_colormap(), 0, 0, 0, 0, deskSz[0], deskSz[1])
    #return Image.fromstring('RGB', (deskSz[0], deskSz[1]), img.get_pixels())
    imgExport = StringIO.StringIO()
    img.save_to_callback(imgExport.write, 'bmp')
    imgExport.seek(0)
    return Image.open(imgExport)

def loadSrcImg():
    # Load source image into OpenCV for manipulation
    # However, first load it into PIL so we can reduce the colour palette size and create an underlay image that will be used to identify image elements
    # Reducing the colour palette size of the underlay image (image quantization) can help to improve element identification through flood fill in some cases
    global srcImgOCV, ulayImg, srcImgSz, srcImgSpwnPt, srcImgContainerSz

    # Open source image
    if args.image == 'screen':
        clrTermLine(1) # Clear the terminal so that the screenshot will look nice
        ulayImgPIL = grabScreen()
        updTermLine('Loading game: Processing image... (larger images/res take longer to process)')
    else:
        try:
            updTermLine('Loading game: Processing image... (larger images/res take longer to process)')
            ulayImgPIL = Image.open(args.image).convert('RGB')
        except IOError:
            clrTermLine()
            print 'Error: Invalid image file'
            quit()

    # Set/modify useful variables
    if args.resolution == [0, 0]:
        args.resolution = ulayImgPIL.size
    modArgs() # Modify cmd-line arguments to make them more useful for programming
    srcImgContainerSz = (args.resolution[0] - args.resolution[0] * args.padding / 100, args.resolution[1] - args.resolution[1] * args.padding / 100)
    ulayImgPIL, srcImgSpwnPt = niceResizeImg(ulayImgPIL, srcImgContainerSz) # Resize image to fit window and get the should-be spawn point
    srcImgSz = ulayImgPIL.size

    # Replace colourKey2 -> colourKey so that Pygame will treat it as transparent
    if args.colourKey2 != None:
        ulayImgPIL = replaceColour(ulayImgPIL, args.colourKey2, args.colourKey)

    # Load source image into OpenCV
    srcImgOCV = cv.CreateImageHeader(srcImgSz, cv.IPL_DEPTH_8U, 3)
    cv.SetData(srcImgOCV, ulayImgPIL.tostring())

    # Modify underlay image colour palette if requested
    # This is highly experimental and in many cases somehow corrupts the image when it gets converted to OpenCV
    if args.colourPalette != None:
        ulayImgPIL = ulayImgPIL.convert('P', palette=Image.ADAPTIVE, colors = args.colourPalette).convert('RGB')
        # Replace colourKey2 -> colourKey again
        if args.colourKey2 != None:
            ulayImgPIL = replaceColour(ulayImgPIL, args.colourKey2, args.colourKey)

    # Load underlay image into OpenCV
    ulayImg = cv.CreateImageHeader(srcImgSz, cv.IPL_DEPTH_8U, 3)
    cv.SetData(ulayImg, ulayImgPIL.tostring())

def replaceColour(PILImg, oldRGB, newRGB):
    # Paint all pixels of oldRGB as newRGB in a PIL image
    imgArr = numpy.array(PILImg)
    mask = numpy.logical_and.reduce([(imgArr[:, :, i] == oldRGB[i]) for i in range(3)])
    for i in range(3):
        imgArr[mask, i] = newRGB[i]
    return Image.fromstring('RGB', PILImg.size, imgArr.tostring())

def getColouredPixels(img):
    # Return the number of pixels that aren't the same as args.colourKey in an OpenCV image
    # This function can take up to a few seconds to execute for large asteroids. Thinking the speed could be improved by using C code via SciPy?
    imgArr = numpy.array(cv.GetMat(img))
    colourKey = args.colourKey
    mask = numpy.logical_and.reduce([imgArr[:, :, i] == colourKey[i] for i in range(3)])
    return mask.size - numpy.count_nonzero(mask)

def niceResizeImg(PILImg, newSize):
    # Resize a PIL image without breaking the aspect ratio
    # Return the padding space that should be between the screen border and the edges of the resized image
    sz = PILImg.size
    if sz == newSize:
        return PILImg, (0, 0)
    origImgAR = float(sz[0]) / sz[1]
    newImgAR = float(newSize[0]) / newSize[1]
    niceSize = list(newSize)
    padding = [0, 0]
    if origImgAR < newImgAR: # Image too high
        niceSize[0] = int(origImgAR * newSize[1])
        padding[0] = int((newSize[0] - niceSize[0]) / 2)
    elif origImgAR > newImgAR: # Image too wide
        niceSize[1] = int(1 / origImgAR * newSize[0])
        padding[1] = int((newSize[1] - niceSize[1]) / 2)
    niceSize = (int(niceSize[0]), int(niceSize[1]))
    if niceSize[0] > PILImg.size[0]:
        rsMthd = Image.BICUBIC
    else:
        rsMthd = Image.ANTIALIAS
    return PILImg.resize(niceSize, rsMthd), tuple(padding)

def syncSrcImg(mode = 0, rect = None):
    # Update the source image from OpenCV -> Pygame
    if rect == None:
        rect = srcImgRect
    if mode == 0 or mode == 1:
        cv.ResetImageROI(srcImgOCV)
        srcImgPyg = pygame.image.frombuffer(srcImgOCV.tostring(), srcImgSz, 'RGB')#.convert()
        #srcImgPyg.set_colorkey(args.colourKey, pygame.RLEACCEL)
        oBgImg.blit(bgImg, rect, rect)
        oBgImg.blit(srcImgPyg, rect, (rect[0] - srcImgSpwnPt[0], rect[1] - srcImgSpwnPt[1], rect[2], rect[3]))
    if mode == 0 or mode == 2:
        winSrfc.blit(oBgImg, rect, rect)

def genBgImg():
    # Generate pygame stars background image
    img = pygame.Surface(args.resolution)
    img.fill(args.backgroundColour)
    starCol = args.starsColour
    c = 0
    nStars = int(args.starsVolume * args.resolution[0] * args.resolution[1])
    while c < nStars:
        c += 1
        if c % 300 == 0:
            # For insane users who request an insane amount of stars - pixel access in Python is slow
            updTermLine('Loading game: Generating background (' + str(round(float(c) / nStars * 100, 2)) + '%)')
        img.set_at((random.randrange(1, args.resolution[0]), random.randrange(1, args.resolution[1])), starCol)
    updTermLine('Loading game...')
    return img

def genAsteroid(pos, fillOnly = 0, bullet = None, sync = 1, offsetTime = 1):
    # Create a new 'asteroid' based on the specified position's region
    global timeOffset
    if offsetTime == 1:
        preRunTime = pygame.time.get_ticks()
    cv.Copy(maskImg, bkMaskImg) # Backup mask
    comp = cv.FloodFill(ulayImg, pos, 0, args.sameColourTolerance, args.sameColourTolerance, args.pixelConnectivity | cv.CV_FLOODFILL_MASK_ONLY, maskImg)
    if comp[2] == (0, 0, 0, 0):
        return
    cv.SetImageROI(maskImg, (comp[2][0] + 1, comp[2][1] + 1, comp[2][2] + 1, comp[2][3] + 1))
    cv.SetImageROI(srcImgOCV, comp[2])
    if fillOnly == 0:
        element = cv.CreateImage((comp[2][2], comp[2][3]), cv.IPL_DEPTH_8U, 3)
        cv.Rectangle(element, (0, 0), (comp[2][2], comp[2][3]), args.colourKey, cv.CV_FILLED)
        cv.Copy(srcImgOCV, element, maskImg)
        if asteroidSuitabilityChk((comp[2][2], comp[2][3]), 2, 1):
            # Asteroids should be made
            # Check that ship doesn't overlap element
            if shipObj != None:
                elementPyg = pygame.image.frombuffer(element.tostring(), (comp[2][2], comp[2][3]), 'RGB')#.convert()
                elementPyg.set_colorkey(args.colourKey)
                elementPygMask = pygame.mask.from_surface(elementPyg)
                shipObjMask = pygame.mask.from_surface(shipObj.image)
                if shipObjMask.overlap(elementPygMask, (-(shipObj.rect.topleft[0] - (srcImgSpwnPt[0] + comp[2][0])), -(shipObj.rect.topleft[1] - (srcImgSpwnPt[1] + comp[2][1])))) != None:
                    # Ship and element overlap
                    # Restore backup mask and don't make asteroids
                    cv.ResetImageROI(maskImg)
                    cv.Copy(bkMaskImg, maskImg)
                    return
            # Split element into two asteroids
            genAsteroidsFromElement(element, (comp[2][0], comp[2][1]), 0, bullet, (comp[2][2], comp[2][3]), updatePD = 1, offsetTime = 0)
        else:
            # Update pixelsDetatched stat anyway
            asteroidSuitabilityChk(element, 3, updatePD = 1)
    cv.SetImageROI(uBgImg, comp[2])
    cv.Copy(uBgImg, srcImgOCV, maskImg)
    cv.ResetImageROI(maskImg)
    maskRect = (comp[2][0] + srcImgSpwnPt[0], comp[2][1] + srcImgSpwnPt[1], comp[2][2], comp[2][3])
    if sync == 1:
        syncSrcImg(rect = maskRect)
    additionalRects.append(maskRect)
    if offsetTime == 1:
        # Go back in time to prevent lag effects
        timeOffset -= pygame.time.get_ticks() - preRunTime

def genAsteroidsFromElement(element, pos, performSzChk = 1, bullet = None, parentSz = None, level = 0, updatePD = 0, offsetTime = 1):
    # Split an element in half and convert the pieces to asteroids
    global timeOffset
    if offsetTime == 1:
        preRunTime = pygame.time.get_ticks()
    elementSz = cv.GetSize(element)
    # Check size suitability first
    if performSzChk == 1 and asteroidSuitabilityChk(elementSz, 2, 1, parentSz) == 0:
        if updatePD == 1:
            # Update pixelsDetatched stat anyway
            asteroidSuitabilityChk(element, 3, updatePD = 1)
        return
    piecesSz = [list(elementSz), list(elementSz)]
    if elementSz[0] > elementSz[1] or elementSz[0] == elementSz[1]:
        # Split element vertically
        piecesSz[0][0] = elementSz[0] / 2
        piecesSz[1][0] = elementSz[0] - piecesSz[0][0]
        splitM = 0
    else:
        # Split element horizontally
        piecesSz[0][1] = elementSz[1] / 2
        piecesSz[1][1] = elementSz[1] - piecesSz[0][1]
        splitM = 1
    pieces = range(2)
    pieces[0] = cv.CreateImage(piecesSz[0], cv.IPL_DEPTH_8U, 3)
    cv.SetImageROI(element, (0, 0) + tuple(piecesSz[0]))
    cv.Copy(element, pieces[0])
    pieces[1] = cv.CreateImage(piecesSz[1], cv.IPL_DEPTH_8U, 3)
    if splitM == 0:
        cv.SetImageROI(element, (piecesSz[0][0], 0) + tuple(piecesSz[1]))
    elif splitM == 1:
        cv.SetImageROI(element, (0, piecesSz[0][1]) + tuple(piecesSz[1]))
    cv.Copy(element, pieces[1])
    piecesPos = range(2)
    piecesPos[0] = list(pos)
    # There's currently an issue here where the pieces appear a pixel apart from each other if they have odd sizes, since the sizes are being treated as integers when they're being divided, so they get rounded. For now the problem is being fixed by an if statement to see if the original size was odd, and then adjust the position accordingly.
    if splitM == 0:
        piecesPos[1] = [pos[0] + piecesSz[1][0], pos[1]]
        if elementSz[0] % 2 == 1:
            piecesPos[1][0] -= 1
    elif splitM == 1:
        piecesPos[1] = [pos[0], pos[1] + piecesSz[1][1]]
        if elementSz[1] % 2 == 1:
            piecesPos[1][1] -= 1
    for i, piece in enumerate(pieces):
        piece, bbox = trimImg(piece, args.colourKey)
        if bbox == None:
            continue
        elif bbox != 0:
            piecesPos[i][0] += bbox[0]
            piecesPos[i][1] += bbox[1]
            piecesSz[i] = cv.GetSize(piece)
        if args.asteroidsMaxSize[0] < piecesSz[i][0] or args.asteroidsMaxSize[1] < piecesSz[i][1]:
            # Split piece into even smaller pieces if it's too big (recursive function call)
            genAsteroidsFromElement(piece, piecesPos[i], bullet = bullet, parentSz = parentSz, level = level, updatePD = updatePD, offsetTime = 0)
        elif asteroidSuitabilityChk(piece, 3, 0, updatePD = updatePD) and (bbox != 0 or asteroidSuitabilityChk(piecesSz[i], 1, 1, parentSz)):
            asteroid(piece, piecesPos[i], bullet, parentSz = parentSz, level = level)
            # Update active asteroids stat
            changeAndRedrawStat(statActiveAsteroidsObj, statActiveAsteroidsObj.value + 1)
            # Update asteroids made stat
            changeAndRedrawStat(statAsteroidsMadeObj, statAsteroidsMadeObj.value + 1)
    if offsetTime == 1:
        # Go back in time to prevent lag effects
        timeOffset -= pygame.time.get_ticks() - preRunTime

def trimImg(img, borderCol):
    # Trim borders from an OpenCV image
    # This function converts OpenCV -> PIL -> OpenCV, not very elegant but it's fast enough and I can't find the ImageChops.difference equivalent in OpenCV
    sz = cv.GetSize(img)
    PILImg = Image.fromstring('RGB', sz, img.tostring())
    borderCol = tuple(borderCol)
    bg = Image.new('RGB', sz, borderCol)
    diff = ImageChops.difference(PILImg, bg)
    bbox = diff.getbbox()
    if bbox == None:
        return img, bbox
    elif bbox != (0, 0) + sz:
        PILImg = PILImg.crop(bbox)
        img = cv.GetImage(cv.fromarray(numpy.array(PILImg)))
        return img, (bbox[0], bbox[1])
    else:
        return img, 0

def asteroidSuitabilityChk(asteroid, t, inputType = 0, parentSz = None, updatePD = 0):
    # Determines if asteroid should be made or not
    # This function needs revisiting
    # t 1 = size check
    # t 2 = size / 2 check
    # t 3 = CPPP check (should be ran exactly once per area filled on source image, to update pixelsDetatched stat)

    # Determine asteroid size
    if inputType == 1 and t < 3:
        sz = asteroid
    else:
        sz = cv.GetSize(asteroid)

    # Calculate minimum size
    if t < 3:
        if parentSz == None:
            aMinSize = args.asteroidsMinSizeLower
        else:
            # This procedure needs revisiting/simplifaction
            aMinSize = [parentSz[0] / args.asteroidsIdealMinSizeDivider, parentSz[1] / args.asteroidsIdealMinSizeDivider]
            if args.asteroidsMinSizeLower[0] > args.asteroidsMinSizeLower[1]:
                aMinLL = args.asteroidsMinSizeLower[1]
            else:
                aMinLL = args.asteroidsMinSizeLower[0]
            if args.asteroidsMinSizeUpper[0] > args.asteroidsMinSizeUpper[1]:
                aMinUU = args.asteroidsMinSizeUpper[1]
            else:
                aMinUU = args.asteroidsMinSizeUpper[0]
            if aMinSize[0] < aMinLL:
                aMinSize[0] = aMinLL
            if aMinSize[1] < aMinLL:
                aMinSize[1] = aMinLL
            if aMinSize[0] > aMinUU:
                aMinSize[0] = aMinUU
            if aMinSize[1] > aMinUU:
                aMinSize[1] = aMinUU
            if aMinSize[0] + aMinSize[1] < args.asteroidsMinSizeLower[0] + args.asteroidsMinSizeLower[1]:
                aMinSize = args.asteroidsMinSizeLower
            if aMinSize[0] + aMinSize[1] > args.asteroidsMinSizeUpper[0] + args.asteroidsMinSizeUpper[1]:
                aMinSize = args.asteroidsMinSizeUpper

    # Get # of coloured pixels on asteroid if it's a CPPP check
    if t == 3:
        CP = getColouredPixels(asteroid)
        # Update pixelsDetatched stat
        if updatePD == 1:
            changeAndRedrawStat(statPixelsDetatchedObj, statPixelsDetatchedObj.value + CP)

    # Run check
    if (
        ((t == 1) and ((aMinSize[0] <= sz[0] and aMinSize[1] <= sz[1]) or (aMinSize[1] <= sz[0] and aMinSize[0] <= sz[1])))
        or ((t == 2) and ((aMinSize[0] <= sz[0] / 2 and aMinSize[1] <= sz[1] / 2) or (aMinSize[1] <= sz[0] / 2 and aMinSize[0] <= sz[1] / 2)))
        or ((t == 3) and float(CP) / (sz[0] * sz[1]) >= args.minColouredPixelsPerPixel)
    ):
        return 1
    else:
        return 0

def gameExitSeq():
    # Exit game peacefully
    pygame.quit()
    sys.exit()

def jumpObj(obj):
    # If parts of an object is out of the range of the screen, make the out-of-range region of it appear on the opposite edge
    # This is achieved by spawning a copy of the object at the 'jumped' co-ordinates
    cpyCo = [None, None]
    if obj.rect.left < 0 and obj.rect.top > 0 and obj.rect.bottom < args.resolution[1]:
        # west -> east
        cpyCo[0] = args.resolution[0] + obj.rect.left
        cpyCo[1] = obj.rect.top
    elif obj.rect.right > args.resolution[0] and obj.rect.top > 0 and obj.rect.bottom < args.resolution[1]:
        # east -> west
        cpyCo[0] = obj.rect.left - args.resolution[0]
        cpyCo[1] = obj.rect.top
    elif obj.rect.top < 0 and obj.rect.left > 0 and obj.rect.right < args.resolution[0]:
        # north -> south
        cpyCo[0] = obj.rect.left
        cpyCo[1] = args.resolution[1] + obj.rect.top
    elif obj.rect.bottom > args.resolution[1] and obj.rect.left > 0 and obj.rect.right < args.resolution[0]:
        # south -> north
        cpyCo[0] = obj.rect.left
        cpyCo[1] = obj.rect.top - args.resolution[1]
    elif obj.rect.left < 0 and obj.rect.top < 0:
        # north west -> south east
        cpyCo[0] = args.resolution[0] + obj.rect.left
        cpyCo[1] = args.resolution[1] + obj.rect.top
    elif obj.rect.right > args.resolution[0] and obj.rect.top < 0:
        # north east -> south west
        cpyCo[0] = obj.rect.left - args.resolution[0]
        cpyCo[1] = args.resolution[1] + obj.rect.top
    elif obj.rect.left < 0 and obj.rect.bottom > args.resolution[1]:
        # south west -> north east
        cpyCo[0] = args.resolution[0] + obj.rect.left
        cpyCo[1] = obj.rect.top - args.resolution[1]
    elif obj.rect.right > args.resolution[0] and obj.rect.bottom > args.resolution[1]:
        # south east -> north west
        cpyCo[0] = obj.rect.left - args.resolution[0]
        cpyCo[1] = obj.rect.top - args.resolution[1]
    if cpyCo != [None, None]:
        if obj.jumpCpy == None:
            # Spawn copy object
            obj.jumpCpy = globals()[obj.__class__.__name__](isJumpCpy = 1)
            obj.jumpCpy.image = obj.image
            obj.jumpCpy.rect = obj.jumpCpy.image.get_rect()
            obj.jumpCpy.rect.topleft = cpyCo
            obj.jumpCpy.nonJumpCpy = obj
        else:
            # Synchronize copy object image and co-ordinates
            obj.jumpCpy.image = obj.image
            obj.jumpCpy.rect.topleft = cpyCo
        #if obj.jumpCpy.rect.top > 0 and obj.jumpCpy.rect.left > 0 and obj.jumpCpy.rect.bottom < args.resolution[1] and obj.jumpCpy.rect.right < args.resolution[0]:
        if obj.rect.colliderect(winRect) == 0:
            # Jump completed
            jumpObj_complete(obj)
    elif cpyCo == [None, None] and obj.jumpCpy != None:
        # Jump cancelled
        jumpObj_complete(obj, 0)

def jumpObj_complete(obj, updOrigObj = 1):
    # Jump process complete, clean up jumpCpy object and update the original object to the new position
    if updOrigObj == 1:
        obj.rect.topleft = obj.jumpCpy.rect.topleft
        obj.jumpMoveUpd()
    obj.jumpCpy.kill()
    obj.jumpCpy = None

def safeKillObj(obj):
    # Kill an object and its jump copy
    # Get object original copy
    obj = obj.nonJumpCpy
    # Kill original copy
    obj.kill()
    # Kill jump copy
    if obj.jumpCpy != None:
        obj.jumpCpy.kill()

def restartGame():
    # Restart game
    global shipObj, gameOverMode, mbStateObj
    cv.Rectangle(maskImg, (0, 0), maskImgSz, 0, cv.CV_FILLED)
    cv.Rectangle(bkMaskImg, (0, 0), maskImgSz, 0, cv.CV_FILLED)
    cv.ResetImageROI(srcImgOCV)
    cv.Copy(origImg, srcImgOCV)
    for g in groups:
        for s in g.sprites():
            s.kill()
    curMks = shipObj.curMks
    shipObj = ship()
    shipObj.mousePosChange(mPos)
    shipObj.curMks = curMks
    syncSrcImg()
    pygame.display.flip()
    updTicks()
    shipObj.updMoveDirection()
    if paused == 1:
        pygame.event.post(pygame.event.Event(pygame.locals.KEYUP, key = pygame.locals.K_p))
    gameOverMode = 0
    for statObj in statsText.sprites():
        changeAndRedrawStat(statObj, 0)
    mbStateObj.lastLaunch = -args.megaBulletRechargeTime

def updTicks():
    # Update game time
    global ticks, ticksSecs
    ticks = pygame.time.get_ticks() + timeOffset
    ticksSecs = ticks / 1000.0

def changeAndRedrawStat(statObj, newValue):
    # Update stat object value and redraw stat text
    statObj.value = newValue
    # Only draw if stats are enabled
    if statsText in updGroups:
        statObj.drawText()

def modArgs():
    # Modify the command-line arguments to make them more useful for programming
    # This is now a bad function that was introduced when the code was about 300 lines long
    if args.colourKey == None:
        args.colourKey = args.backgroundColour
    args.sameColourTolerance = (args.sameColourTolerance, args.sameColourTolerance, args.sameColourTolerance)
    args.asteroidsMaxSize = (args.resolution[0] * args.asteroidsMaxSize / 100, args.resolution[1] * args.asteroidsMaxSize / 100)
    # The below is some backwards-compatibility for arguments that no longer exist in their current form that are referenced in functions. Ideally the references should actually be changed to suit the new argument form.
    # update: currently irrelevant
    #args.asteroidsMinSize1 = (args.asteroidsMinSize[0], args.asteroidsMinSize[1])
    #args.asteroidsMinSize2 = (args.asteroidsMinSize[1], args.asteroidsMinSize[0])

def replaceLowerArgs(normArgs):
    # Replace lowercased cmd-line arguments -> normal case
    for normArg in normArgs:
        lowerArg = normArg.lower()
        for i in range(sys.argv.count(lowerArg)):
            sys.argv.append(normArg)
            sys.argv.remove(lowerArg)

def arg_type_percentage1(inp):
    # float between 0 =< inp <= 100
    try:
        inp = float(inp)
    except ValueError:
        pass
    if type(inp) != float or inp > 100 or inp < 0:
        raise argparse.ArgumentTypeError('percentage must be between 0-100')
    return inp

def arg_type_percentage2(inp):
    # float between 0 =< inp < 100
    try:
        inp = float(inp)
    except ValueError:
        pass
    if type(inp) != float or inp >= 100 or inp < 0:
        raise argparse.ArgumentTypeError('percentage must be between 0-99.9...')
    return inp

def arg_type_RGB(inp):
    # int between 0 <= 255
    try:
        inp = int(inp)
    except ValueError:
        pass
    if type(inp) != int or inp > 255 or inp < 0:
        raise argparse.ArgumentTypeError('RGB value must between 0-255')
    return inp

def arg_type_file(inp):
    # an existant file
    if os.path.isfile(inp) == False and inp != 'screen':
        raise argparse.ArgumentTypeError('no such file \'' + inp + '\'')
    return inp

# Define prank mode exit keyword
pmExitKw = 'stopit'

# Process command-line arguments
import argparse, os.path, sys

if len(sys.argv) == 1:
    progPrefix = ('python ' if sys.argv[0][0] + sys.argv[0][1] != './' else '') + sys.argv[0]
    # I've textwrapped this manually to 80 characters per line for now, as I can't seem to get Python's textwrap module to wrap it elegantly
    print """Asteroids - with an image of your choice! Pixel Piroid automagically identifies
the different elements of your image (based on colour difference) and converts
them to destroyable 'asteroids'. Destroy the asteroids before they destroy your
ship.

Please specify the path of the image you'd like to destroy.
i.e. """ + progPrefix + """ image-path

Try the following for some examples:
""" + progPrefix + """ --screen (Destroy your desktop/computer screen!)
""" + progPrefix + """ rasp.png (RPi logo)
""" + progPrefix + """ rasp.png -cp 2 -bg 0 0 0 -ck2 255 255 255 (RPi logo)

You're encouraged to experiment with your own images, including photographs. See
below for adjusting element identification.

Use the LEFT mouse button to destroy existing asteroids. Use the RIGHT mouse
button to create new asteroids from the image. Press ESC to exit fullscreen
mode. Press C or SHIFT to launch the mega bullet. Use WASD/arrow keys to move.

Increase the same colour tolerance (the -sct flag) if too little of the image is
being selected for new asteroids, decrease it if too much is being selected.
See readme.txt for more details on improving element detection.

Run '""" + progPrefix + """ -h' for extra help, or see readme.txt."""
    quit()

# Help people who use lowercased mode arguments
replaceLowerArgs(('--prankMode', '--screensaverMode'))

argparser = argparse.ArgumentParser(
    description = 'Asteroids - with an image of your choice! Pixel Piroid automagically identifies the different elements of your image (based on colour difference) and converts them to destroyable \'asteroids\'. Destroy the asteroids before they destroy your ship.',
    epilog = 'Use the LEFT mouse button to destroy existing asteroids. Use the RIGHT mouse button to create new asteroids from the image. Press ESC to exit fullscreen mode. Press C or SHIFT to launch the mega bullet. Use WASD/arrow keys to move.'
)

screenMode = sum([sys.argv.count(arg) for arg in ('-s', '--screen', '-pm', '--prankMode')])

if screenMode != 1:
    argparser.add_argument('image', help = 'path of image to destroy (use \'screen\' for a screenshot of the current screen) (required)', metavar = 'image-path', type = arg_type_file)

argparser.add_argument(
    '-r',
    '--resolution',
    help = 'size of display resolution, use 0x0 to use the original image resolution (default: 640x480)',
    metavar = ('x', 'y'),
    nargs = 2,
    default = (640, 480),
    type = int
)
argparser.add_argument(
    '-mr',
    '--monitorResolution',
    help = 'set the display resolution to the current monitor resolution',
    action = 'count',
    default = 0
)
argparser.add_argument(
    '-p',
    '--padding',
    help = 'percentage padding space between the screen border and the edges of the image (default: 20)',
    metavar = 'percent',
    default = 20,
    type = arg_type_percentage2
)
argparser.add_argument(
    '-fs',
    '--fullscreen',
    help = 'enable fullscreen mode',
    action = 'count',
    default = 0
)
argparser.add_argument(
    '-f',
    '--full',
    help = 'equivalent to \'--fullscreen --monitorResolution --padding 0\'',
    action = 'count',
    default = 0
)
argparser.add_argument(
    '-s',
    '--screen',
    help = 'equivalent to \'screen --full --starsVolume 0 --dontChangeCursor --hideStats\'',
    action = 'count',
    default = 0
)
argparser.add_argument(
    '-pm',
    '--prankMode',
    help = 'enable prank mode; type \'' + pmExitKw + '\' to exit prank mode',
    action = 'count',
    default = 0
)
argparser.add_argument(
    '-sm',
    '--screensaverMode',
    help = 'enable screensaver mode',
    action = 'count',
    default = 0
)
argparser.add_argument(
    '-snad',
    '--screensaverNewAsteroidDelay',
    help = 'time in seconds to wait in between trying to create new asteroids (default: 3)',
    metavar = 'seconds',
    default = 3,
    type = float
)
argparser.add_argument(
    '-sead',
    '--screensaverExistingAsteroidDelay',
    help = 'time in seconds to wait in between destroying existing asteroids (default: 1)',
    metavar = 'seconds',
    default = 1,
    type = float
)
argparser.add_argument(
    '-bg',
    '--backgroundColour',
    help = 'RGB value of game background colour (default: 255 255 255)',
    metavar = ('r', 'g', 'b'),
    nargs = 3,
    default = (255, 255, 255),
    type = arg_type_RGB
)
argparser.add_argument(
    '-ck',
    '--colourKey',
    help = 'RGB value of image colour key; pixels of this colour will be transparent (default: backgroundColour)',
    metavar = ('r', 'g', 'b'),
    nargs = 3,
    type = arg_type_RGB
)
argparser.add_argument(
    '-ck2',
    '--colourKey2',
    help = 'RGB value of the secondary colour key (default: none)',
    metavar = ('r', 'g', 'b'),
    nargs = 3,
    type = arg_type_RGB
)
argparser.add_argument(
    '-sv',
    '--starsVolume',
    help = 'percentage of background pixels that are \'stars\' (default for black background: 0.00125, otherwise: 0)',
    metavar = 'percent',
    type = arg_type_percentage2
)
argparser.add_argument(
    '-sc',
    '--starsColour',
    help = 'RGB value of stars colour (default: backgroundColour inverted)',
    metavar = ('r', 'g', 'b'),
    nargs = 3,
    type = arg_type_RGB
)
argparser.add_argument(
    '-sct',
    '--sameColourTolerance',
    help = 'band value difference of what RGB values are considered to be the same colour when identifying connected pixels (default: 10)',
    metavar = 'band difference',
    default = 10,
    type = arg_type_RGB
)
argparser.add_argument(
    '-pc',
    '--pixelConnectivity',
    help = 'pixel connectivity value (4 or 8) when searching for connected neighbouring pixels (default: 4)',
    metavar = 'value',
    default = 4,
    choices = (4, 8),
    type = int
)
argparser.add_argument(
    '-pfps',
    '--printFPS',
    help = 'print FPS rate to the terminal',
    action = 'count',
    default = 0
)
argparser.add_argument(
    '-dfps',
    '--displayFPS',
    help = 'display FPS on-screen (press f to toggle)',
    action = 'count',
    default = 0
)
argparser.add_argument(
    '-fp',
    '--fillPos',
    help = '(x, y) co-ordinates to fill with transparency before the game begins',
    metavar = ('x', 'y'),
    nargs = 2,
    type = int
)
argparser.add_argument(
    '-aminl',
    '--asteroidsMinSizeLower',
    help = '(x, y) lower range allowed size of the smallest asteroid (default: 5x20)',
    metavar = ('x', 'y'),
    default = (5, 20),
    nargs = 2,
    type = int
)
argparser.add_argument(
    '-aminu',
    '--asteroidsMinSizeUpper',
    help = '(x, y) upper range allowed size of the smallest asteroid (default: 40x40)',
    metavar = ('x', 'y'),
    default = (40, 40),
    nargs = 2,
    type = int
)
argparser.add_argument(
    '-amind',
    '--asteroidsIdealMinSizeDivider',
    help = 'the ideal minimum size of asteroids will be their parent asteroid size divided by this number; if the dimensions don\'t fit the allowed range (see above) the range will be used instead',
    metavar = 'divider',
    default = 10,
    type = float
)
argparser.add_argument(
    '-amax',
    '--asteroidsMaxSize',
    help = 'maximum allowed size of an asteroid, expressed as a percentage of the display resolution (default: 40)',
    metavar = 'percentage',
    default = 40,
    type = arg_type_percentage1
)
argparser.add_argument(
    '-aiv',
    '--asteroidsInitialVelocity',
    help = 'pixels per second initial velocity of asteroids (default: 90)',
    metavar = 'PPS',
    default = 90,
    type = float
)
argparser.add_argument(
    '-avi',
    '--asteroidsVelocityIncrement',
    help = 'pixels per second to increase asteroids velocity by as they get smaller (default: 35)',
    metavar = 'PPS',
    default = 35,
    type = float
)
argparser.add_argument(
    '-mcppp',
    '--minColouredPixelsPerPixel',
    help = 'minimum number of non-transparent pixels per pixel in an asteroid (default: 0.25)',
    metavar = 'pixels',
    default = 0.25,
    type = float
)
argparser.add_argument(
    '-cp',
    '--colourPalette',
    help = 'size of colour palette of underlay image used for identifying elements/asteroids (default: unchanged)',
    metavar = 'colours',
    type = int
)
argparser.add_argument(
    '-ss',
    '--shipSize',
    help = '(x, y) size of space ship (default: 41x40)',
    metavar = ('x', 'y'),
    default = (41, 40),
    nargs = 2,
    type = int
)
argparser.add_argument(
    '-st',
    '--shipThickness',
    help = 'pixel thickness of ship borders, use 0 to fill the ship (default: 3)',
    metavar = 'pixels',
    default = 3,
    type = int
)
argparser.add_argument(
    '-ssp',
    '--shipSpawnPos',
    help = '(x, y) starting position of ship (default: (10, 10))',
    metavar = ('x', 'y'),
    default = (10, 10),
    nargs = 2,
    type = int
)
argparser.add_argument(
    '-sve',
    '--shipVelocity',
    help = 'pixels per second velocity of ship (default: 350)',
    metavar = 'PPS',
    default = 350,
    type = float
)
argparser.add_argument(
    '-sco',
    '--shipColour',
    help = 'RGB value of ship colour (default: backgroundColour inverted)',
    metavar = ('r', 'g', 'b'),
    nargs = 3,
    type = arg_type_RGB
)
argparser.add_argument(
    '-bc',
    '--bulletsColour',
    help = 'RGB value of bullets colour (default: red)',
    metavar = ('r', 'g', 'b'),
    default = (255, 0, 0),
    nargs = 3,
    type = arg_type_RGB
)
argparser.add_argument(
    '-bs',
    '--bulletsSize',
    help = '(x, y) size of bullets (default: 3x15)',
    metavar = ('x', 'y'),
    default = (3, 15),
    nargs = 2,
    type = int
)
argparser.add_argument(
    '-bd',
    '--bulletsDelay',
    help = 'minimum time delay between bullet shots in seconds (default: 0.2)',
    metavar = 'seconds',
    default = 0.2,
    type = float
)
argparser.add_argument(
    '-bv',
    '--bulletVelocity',
    help = 'pixels per second velocity of bullets (default: 800)',
    metavar = 'PPS',
    default = 800,
    type = float
)
argparser.add_argument(
    '-br',
    '--bulletsRange',
    help = 'maximum number of pixels bullets can travel (default: the diagonal distance of the resolution)',
    metavar = 'pixels',
    type = int
)
argparser.add_argument(
    '-dcc',
    '--dontChangeCursor',
    help = 'keep default system cursor',
    action = 'count',
    default = 0
)
argparser.add_argument(
    '-tc',
    '--textColour',
    help = 'RGB value of text colour (default: dark orange)',
    metavar = ('r', 'g', 'b'),
    default = (255, 25, 0),
    nargs = 3,
    type = arg_type_RGB
)
argparser.add_argument(
    '-tf',
    '--textFont',
    help = 'text font file (default: freesansbold.ttf)',
    metavar = 'file',
    default = 'freesansbold.ttf',
    type = str
)
argparser.add_argument(
    '-tbs',
    '--textBigSize',
    help = 'pixel height font size of big text (default: 20)',
    metavar = 'pixels',
    default = 30,
    type = int
)
argparser.add_argument(
    '-tss',
    '--textSmallSize',
    help = 'pixel height font size of small text (default: 10)',
    metavar = 'pixels',
    default = 18,
    type = int
)
argparser.add_argument(
    '-fps',
    '--fps',
    help = 'frames per second rate of game runtime (default: 30)',
    metavar = 'FPS',
    default = 30,
    type = float
)
argparser.add_argument(
    '-hs',
    '--hideStats',
    help = 'don\'t show game statistics by default (press t to toggle)',
    action = 'count',
    default = 0
)
argparser.add_argument(
    '-mbrt',
    '--megaBulletRechargeTime',
    help = 'time in seconds it takes for the mega bullet to recharge (default: 30)',
    metavar = 'seconds',
    default = 30,
    type = float
)
argparser.add_argument(
    '-mbn',
    '--megaBulletNum',
    help = 'number of bullets the mega bullet consists of (default: 25)',
    metavar = 'number',
    default = 25,
    type = int
)
argparser.add_argument(
    '-mbr',
    '--megaBulletRange',
    help = 'maximum number of pixels mega bullets can travel (default: bulletsRange * 3)',
    metavar = 'pixels',
    type = int
)

args = argparser.parse_args()

# Interpret modes
if args.screensaverMode == 1:
    args.full += 1

if screenMode == 1:
    if args.screensaverMode != 1:
        args.full += 1
    args.image = 'screen'
    args.starsVolume = 0
    args.dontChangeCursor += 1
    args.hideStats += 1

if args.full == 1:
    args.fullscreen += 1
    args.monitorResolution += 1
    args.padding = 0

# Prevent GTK from complaining of 'Missing argument for --screen'
if '--screen' in sys.argv:
    sys.argv.remove('--screen')

# TODO: Add more bad argument checking. (Although, I'm too lazy and would rather spend time on the actual game than worry about users who try insane values.)

# Import modules
importMods((
    ('numpy', 0, 'Scientific Computing Tools for Python: NumPy', 'python-numpy'),
    ('random', 0, 'Pseudo-random number generator'),
    ('math', 0, 'Maths'),
    ('pygame', 0, 'Pygame', 'python-pygame'),
    ('pygame.locals', 0, 'Pygame constants'),
    ('cv', 0, 'OpenCV (Open Computer Vision)', 'python-opencv'),
    ('Image', 0, 'Python Imaging Library', 'python-imaging'),
    ('ImageChops', 0, 'Python Imaging Library: Channel Operations'),
    ('StringIO', 0, 'StringIO'),
    (('gtk', 0, 'GTK (Gimp Toolkit)', 'python-gtk2') if args.image == 'screen' else 0), # GTK only needed for taking a screenshot
))

# Asteroid object class
class asteroid(pygame.sprite.Sprite):
    # Initialize asteroid properties
    def __init__(self, element = None, pos = None, bullet = None, isJumpCpy = 0, parentSz = None, level = 0):

        # Initialize sprite
        pygame.sprite.Sprite.__init__(self)
        self.add(asteroids)
        self.isJumpCpy = isJumpCpy
        if isJumpCpy == 1:
            return

        # Create asteroid surface
        self.image = pygame.image.frombuffer(element.tostring(), cv.GetSize(element), 'RGB').convert()
        self.image.set_colorkey(args.colourKey, pygame.RLEACCEL)
        self.rect = self.image.get_rect()
        self.rect.topleft = (pos[0] + srcImgSpwnPt[0], pos[1] + srcImgSpwnPt[1])

        # Set asteroid properties
        self.bullet = bullet # Source bullet
        self.element = element
        self.movePos = self.calcMovePos()
        self.startMoveTime = ticksSecs
        self.preMovePos = self.rect.center
        self.jumpCpy = None
        self.nonJumpCpy = self
        self.parentSz = parentSz
        self.level = level
        self.velocity = self.calcVelocity()

    # Determine asteroid moving direction
    # Calculate random moving angle that is on the opposite side of the normal of the bullet's moving direction
    def calcMovePos(self):
        if self.bullet == None:
            newAngle = math.radians(random.randrange(-180, 180))
        else:
            bulletAngle = math.degrees(self.bullet.angle)
            newAngle = math.radians(random.randrange(int(bulletAngle - 90), int(bulletAngle + 90)))
        return (-math.sin(newAngle), -math.cos(newAngle))

    # Calculate asteroid velocity
    # The deeper the asteroid level, the higher the velocity
    def calcVelocity(self):
        return args.asteroidsInitialVelocity + args.asteroidsVelocityIncrement * self.level

    # Update asteroid co-ordinates
    def update(self):
        # Only update if this object isn't a jump dummy/copy
        if self.isJumpCpy == 1:
            return
        # Jump asteroid if parts of it is out of range
        jumpObj(self)
        # Calculate asteroid theoretical co-ordinates
        thPos = calcTheoreticalPos(self.startMoveTime, self.movePos, self.velocity)
        # Update asteroid co-ordinates
        self.rect.center = (thPos[0] + self.preMovePos[0], thPos[1] + self.preMovePos[1])

    # Reset move properties after asteroid has finished 'jumping'
    def jumpMoveUpd(self):
        self.startMoveTime = ticksSecs
        self.preMovePos = self.rect.center

    # Split asteroid -> 2 asteroids
    def newAsteroids(self, bullet = None):
        preGenTotalAsteroidObjs = len(asteroids.sprites())
        genAsteroidsFromElement(self.nonJumpCpy.element, (self.rect.left - srcImgSpwnPt[0], self.rect.top - srcImgSpwnPt[1]), bullet = bullet, parentSz = self.parentSz, level = self.level + 1)
        if len(asteroids.sprites()) - preGenTotalAsteroidObjs > 0:
            # Update/fix asteroids made stat
            changeAndRedrawStat(statAsteroidsMadeObj, statAsteroidsMadeObj.value - 1)
        safeKillObj(self)

# Ship object class
class ship(pygame.sprite.Sprite):
    # Initialize ship properties
    def __init__(self, isJumpCpy = 0):

        # Initialize sprite
        pygame.sprite.Sprite.__init__(self)
        self.add(shipGrp)
        self.isJumpCpy = isJumpCpy
        if isJumpCpy == 1:
            return

        # Create ship surface
        self.image = pygame.Surface(args.shipSize)
        self.image.set_colorkey(args.colourKey, pygame.RLEACCEL)
        self.rect = self.image.get_rect()

        # Draw ship
        pygame.draw.rect(self.image, args.colourKey, self.rect)
        pygame.draw.polygon(self.image, args.shipColour, (
            # Polygon co-ordinates
            (0, args.shipSize[1]),
            (args.shipSize[0] / 2, 0),
            args.shipSize,
            (args.shipSize[0] / 2,
            args.shipSize[1] / 2)
        ), args.shipThickness)

        # Set ship properties
        self.rect.topleft = args.shipSpawnPos
        self.orig = self.image
        self.direction = 0
        self.movePos = (0, 0)
        self.moveStartTime = 0
        self.thPos = (0, 0)
        self.preMovePos = self.rect.center
        self.angle = 0
        self.jumpCpy = None
        self.nonJumpCpy = self
        self.curMks = []
        self.velocity = args.shipVelocity

        # Define movement keys
        self.mks = range(4)
        self.mks[0] = (pygame.locals.K_UP, pygame.locals.K_w) # Forward
        self.mks[1] = (pygame.locals.K_DOWN, pygame.locals.K_s) # Backward
        self.mks[2] = (pygame.locals.K_LEFT, pygame.locals.K_a) # Leftward
        self.mks[3] = (pygame.locals.K_RIGHT, pygame.locals.K_d) # Rightward

    # Rotate ship according to new mouse position
    def mousePosChange(self, newPos):
        # Calculate new ship angle based on mouse co-ordinates and ship co-ordinates
        self.angle = math.atan2(self.rect.center[0] - newPos[0], self.rect.center[1] - newPos[1])
        self.image = pygame.transform.rotate(self.orig, math.degrees(self.angle))
        curPos = self.rect.center
        self.rect = self.image.get_rect()
        self.rect.center = curPos
        # Update moving direction
        self.prepMove(self.direction, 1)

    # Calculate the direction the ship should move based on its current angle
    def calcMovePos(self, direction):
        if direction == 1:
            # Forward
            return (-math.sin(self.angle), -math.cos(self.angle))
        elif direction == 2:
            # Backward
            return (math.sin(self.angle), math.cos(self.angle))
        elif direction == 3:
            # Left
            return (math.sin(self.angle - math.radians(90)), math.cos(self.angle - math.radians(90)))
        elif direction == 4:
            # Right
            return (math.sin(self.angle + math.radians(90)), math.cos(self.angle + math.radians(90)))
        elif direction == 5:
            # Forward left
            return (-math.sin(self.angle + math.radians(45)), -math.cos(self.angle + math.radians(45)))
        elif direction == 6:
            # Forward right
            return (-math.sin(self.angle - math.radians(45)), -math.cos(self.angle - math.radians(45)))
        elif direction == 7:
            # Backward left
            return (math.sin(self.angle + math.radians(45)), math.cos(self.angle + math.radians(45)))
        elif direction == 8:
            # Backward right
            return (math.sin(self.angle - math.radians(45)), math.cos(self.angle - math.radians(45)))

    # Prepare ship to move
    def prepMove(self, direction, callType = 0):
        self.direction = direction
        if direction == 0 or callType == 1:
            self.preMovePos = self.rect.center
        if direction != 0:
            self.movePos = self.calcMovePos(self.direction)
            self.startMoveTime = ticksSecs
            if callType == 1:
                # If the ship is rotating whilst it's moving, it will seem as if it has stalled as the co-ordinates will constantly be rounded to (0, 0) as self.startMoveTime is being reset many times. So, push forward self.startMoveTime slightly to prevent the co-ordinates from being rounded to (0, 0).
                # This value is currently optimised for a ship velocity of 250-350ish PPS and an FPS rate of around 30. I'm unsure how the values for other velocities/FPS rates can be calculated.
                self.startMoveTime -= 0.04

    # Update ship co-ordinates
    def update(self):
        # Only update if this object isn't a jump dummy/copy
        if self.isJumpCpy == 1:
            return
        # Update asteroid direction if necessary
        if self.direction > 2:
            self.mousePosChange(mPos)
        # Jump ship if parts of it is out of range
        jumpObj(self)
        # Only move ship if the direction is moving (0 < direction <= 4)
        if self.direction != 0:
            # Get ship theoretical co-ordinates
            thPos = calcTheoreticalPos(self.startMoveTime, self.movePos, self.velocity)
            # Update ship co-ordinates
            self.rect.center = (thPos[0] + self.preMovePos[0], thPos[1] + self.preMovePos[1])

    # Reset startMoveTime after ship has finished 'jumping'
    def jumpMoveUpd(self):
        direction = self.direction
        self.prepMove(0)
        self.prepMove(direction)

    # Determine which way to move ship in accordance to what movement keys are being pressed
    def updMoveDirection(self):
        # Reset move properties first/stop moving ship
        self.prepMove(0)
        if len(self.curMks) == 1:
            # Move non-diagonally
            for i, ks in enumerate(self.mks):
                if self.curMks[0] in ks:
                    self.prepMove(i + 1)
        elif len(self.curMks) == 2:
            # Move diagonally
            if (self.curMks[0] in self.mks[0] and self.curMks[1] in self.mks[2]) or (self.curMks[0] in self.mks[2] and self.curMks[1] in self.mks[0]):
                self.prepMove(5)
            elif (self.curMks[0] in self.mks[0] and self.curMks[1] in self.mks[3]) or (self.curMks[0] in self.mks[3] and self.curMks[1] in self.mks[0]):
                self.prepMove(6)
            elif (self.curMks[0] in self.mks[1] and self.curMks[1] in self.mks[2]) or (self.curMks[0] in self.mks[2] and self.curMks[1] in self.mks[1]):
                self.prepMove(7)
            elif (self.curMks[0] in self.mks[1] and self.curMks[1] in self.mks[3]) or (self.curMks[0] in self.mks[3] and self.curMks[1] in self.mks[1]):
                self.prepMove(8)

# Bullet object class
class bullet(pygame.sprite.Sprite):
    # Initialize bullet properties
    def __init__(self, isJumpCpy = 0, angle = None, randColour = 0, travelRange = None):

        # Initialize sprite
        pygame.sprite.Sprite.__init__(self)
        self.add(bullets)
        self.isJumpCpy = isJumpCpy
        if isJumpCpy == 1:
            return

        # Set angle/calculate move position
        if angle == None:
            self.angle = shipObj.angle
            self.movePos = shipObj.calcMovePos(1)
        else:
            self.angle = angle
            self.movePos = (-math.sin(angle), -math.cos(angle))

        # Set colour
        if randColour == 1:
            self.colour = (random.randrange(0, 256), random.randrange(0, 256), random.randrange(0, 256))
        else:
            self.colour = args.bulletsColour

        # Create bullet surface
        self.image = pygame.Surface(args.bulletsSize)
        self.image.set_colorkey(args.colourKey, pygame.RLEACCEL)
        self.rect = self.image.get_rect()

        # Draw bullet
        pygame.draw.rect(self.image, self.colour, self.rect)
        self.image = pygame.transform.rotate(self.image, math.degrees(self.angle))

        # Set bullet properties
        self.rect.topleft = self.calcStartPos()
        self.genAsteroid = None
        self.moveStartTime = ticksSecs
        self.preMovePos = self.rect.center
        self.preMoveRect = self.rect.copy()
        self.jumpCpy = None
        self.spawnTime = ticksSecs
        self.genAsteroid = None
        self.nonJumpCpy = self
        self.velocity = args.bulletVelocity

        if travelRange == None:
            self.travelRange = args.bulletsRange
        else:
            self.travelRange = travelRange

    # Calculate what the starting co-ordinates of the bullet should be according to the ship's angle and co-ordinates
    def calcStartPos(self):
        shipHalfHeight = args.shipSize[0] / 2
        return (self.movePos[0] * shipHalfHeight + shipObj.rect.center[0], self.movePos[1] * shipHalfHeight + shipObj.rect.center[1])

    # Update bullet co-ordinates
    def update(self):
        if self.isJumpCpy == 1:
            # Only update if this object isn't a jump dummy/copy
            return
        elif self.genAsteroid != None and objHasHitTarget(self.genAsteroid, self.preMoveRect, self.rect, self.angle) == 1:
            # Check if bullet has reached target asteroid area if self.genAsteroid is set
            # Generate new asteroid and kill bullet
            if srcImgSpwnPt[0] < self.genAsteroid[0] < srcImgSz[0] + srcImgSpwnPt[0] and srcImgSpwnPt[1] < self.genAsteroid[1] < srcImgSz[1] + srcImgSpwnPt[1]:
                # Generate new asteroid if target is within source image area
                genAsteroid((self.genAsteroid[0] - srcImgSpwnPt[0], self.genAsteroid[1] - srcImgSpwnPt[1]), 0, bullet = self)
            # Kill bullet
            safeKillObj(self)
        elif (ticksSecs - self.spawnTime) * self.velocity >= self.travelRange:
            # Kill bullet if it has travelled the maximum range
            safeKillObj(self)
            return
        # Jump bullet if parts of it is out of range
        if self.genAsteroid == None:
            jumpObj(self)
        # Get bullet theoretical co-ordinates
        thPos = calcTheoreticalPos(self.moveStartTime, self.movePos, self.velocity)
        # Update bullet co-ordinates
        self.rect.center = (thPos[0] + self.preMovePos[0], thPos[1] + self.preMovePos[1])

    # Reset move properties after bullet has finished 'jumping'
    def jumpMoveUpd(self):
        self.moveStartTime = ticksSecs
        self.preMovePos = self.rect.center

# Sprite class for cursor rect
class cursorRectSprite(pygame.sprite.Sprite):
    def __init__(self):
        pygame.sprite.Sprite.__init__(self)
        self.rect = pygame.Rect(0, 0, 48, 48)

# Pause text object
class pauseText(pygame.sprite.Sprite):
    def __init__(self):
        pygame.sprite.Sprite.__init__(self)
        # Draw pause text
        self.image = bigFont.render('|| Paused', 1, args.textColour)
        self.rect = self.image.get_rect()
        self.rect.right = args.resolution[0] - 50
        self.rect.top = 50

# Game over text object
class gameOverText(pygame.sprite.Sprite):
    def __init__(self):
        pygame.sprite.Sprite.__init__(self)
        # Draw game over text
        text1 = bigFont.render('Game Over', 1, args.textColour)
        text2 = smallFont.render('Press R to restart', 1, args.textColour)
        text1Rect = text1.get_rect()
        text2Rect = text2.get_rect()
        sz = [0] * 2
        sz[1] = text1Rect.bottom + text2Rect.bottom
        if text1Rect.right > text2Rect.right:
            sz[0] = text1Rect.right
        else:
            sz[0] = text2Rect.right
        self.image = pygame.Surface(sz, pygame.locals.SRCALPHA)
        self.image.fill((0, 0, 0, 0))
        self.rect = self.image.get_rect()
        self.rect.center = centerPt
        self.image.blit(text1, ((sz[0] - text1Rect.right) / 2, 0))
        self.image.blit(text2, ((sz[0] - text2Rect.right) / 2, text1Rect.bottom))

# Stat text object: pixels detatched
class statPixelsDetatched(pygame.sprite.Sprite):

    # Initialize
    def __init__(self):
        pygame.sprite.Sprite.__init__(self)
        self.add(statsText)
        self.value = 0
        self.drawText()

    # Draw/redraw text
    def drawText(self):
        # Draw
        self.image = smallFont.render(str(round((float(self.value) / srcImgColouredPixels) * 100, 2)) + '% pixels detatched', 1, args.textColour)
        # Update rect
        self.rect = self.image.get_rect()
        self.rect.right = args.resolution[0] - 20
        self.rect.bottom = args.resolution[1] - 20

# Stat text object: asteroids made
class statAsteroidsMade(pygame.sprite.Sprite):

    # Initialize
    def __init__(self):
        pygame.sprite.Sprite.__init__(self)
        self.add(statsText)
        self.value = 0
        self.drawText()

    # Draw/redraw text
    def drawText(self):
        # Draw
        self.image = smallFont.render(str(self.value) + ' asteroids made', 1, args.textColour)
        # Update rect
        self.rect = self.image.get_rect()
        self.rect.right = args.resolution[0] - 20
        self.rect.bottom = statPixelsDetatchedObj.rect.top

# Stat text object: active asteroids
class statActiveAsteroids(pygame.sprite.Sprite):

    # Initialize
    def __init__(self):
        pygame.sprite.Sprite.__init__(self)
        self.add(statsText)
        self.value = 0
        self.drawText()

    # Draw/redraw text
    def drawText(self):
        # Draw
        self.image = smallFont.render(str(self.value) + ' active asteroids', 1, args.textColour)
        # Update rect
        self.rect = self.image.get_rect()
        self.rect.right = args.resolution[0] - 20
        self.rect.bottom = statAsteroidsMadeObj.rect.top

    # Self-update value (not a currently used function)
    def updateValue(self):
        activeAsteroids = 0
        for a in asteroids.sprites():
            if a.isJumpCpy == 0:
                activeAsteroids += 1
        changeAndRedrawStat(self, activeAsteroids)

# FPS state object
class FPSState(pygame.sprite.Sprite):

    # Initialize
    def __init__(self):
        pygame.sprite.Sprite.__init__(self)
        self.add(FPSStateGrp)
        self.lastUpdate = -0.25 * 1000

    # Update FPS text
    def update(self):
        # Only update every 0.25 seconds
        if ticks - self.lastUpdate < 250:
            return
        # Draw
        self.image = smallFont.render('FPS: ' + str(round(fpsClock.get_fps(), 2)), 1, args.textColour)
        # Update rect
        self.rect = self.image.get_rect()
        self.rect.left = 20
        self.rect.top = 20
        # Update self.lastUpdate
        self.lastUpdate = ticks

# Mega bullet status message object (stat text)
class mbState(pygame.sprite.Sprite):

    # Initialize
    def __init__(self):
        pygame.sprite.Sprite.__init__(self)
        self.add(statsText)
        self.lastLaunch = -args.megaBulletRechargeTime
        self.visible = 0

        # Draw message text/set rect
        self.image = smallFont.render('Mega bullet ready', 1, args.textColour)
        self.rect = self.image.get_rect()

    # Update visibility if invisible
    def update(self):
        if self.visible == 0 and ticksSecs - self.lastLaunch > args.megaBulletRechargeTime:
            # Make visible
            self.rect.right = args.resolution[0] - 20
            self.rect.bottom = statActiveAsteroidsObj.rect.top
            self.visible = 1

    # Make invisible
    def invisible(self):
        self.rect.topleft = args.resolution
        self.visible = 0

    # Empty function called when toggling stats on
    def drawText(self):
        pass

# Prepare game
# In hindsight this should have been done as a class object or two

# Get monitor resolution if the --monitorResolution flag is set
# Initialize the game early as that's the only way to get the resolution
if args.monitorResolution == 1:
    pygame.init()
    dispInfo = pygame.display.Info()
    args.resolution = (dispInfo.current_w, dispInfo.current_h)

# Load source image
loadSrcImg()

# Initialize game
updTermLine('Loading game...')
if args.monitorResolution != 1:
    pygame.init()
pygame.display.set_caption('Pixel Piroid | Asteroids - with an image of your choice!')
fpsClock = pygame.time.Clock()

# Set cursor
if args.dontChangeCursor != 1:
    cursor = pygame.cursors.broken_x
else:
    cursor = pygame.cursors.arrow
pygame.mouse.set_cursor(*cursor)

# Set useful game variables
srcImgSpwnPt = (int(srcImgSpwnPt[0] + (args.resolution[0] - srcImgContainerSz[0]) / 2), int(srcImgSpwnPt[1] + (args.resolution[1] - srcImgContainerSz[1]) / 2))
bgInvertedCol = (abs(args.backgroundColour[0] - 255), abs(args.backgroundColour[1] - 255), abs(args.backgroundColour[2] - 255)) # Invert background colour
additionalRects = []
curMks = [] # Current movement keys that are being pressed
lastBulletShot = -args.bulletsDelay
centerPt = (args.resolution[0] / 2, args.resolution[1] / 2)
mPos = centerPt
timeOffset = 0
winRect = pygame.Rect((0, 0) + args.resolution)
paused = 0
prePauseTime = None
fpsRate = args.fps
lastGameOverChk = 0
gameOverMode = 0
latestChrs = [''] * len(pmExitKw)
ssLastNewAsteroid = -args.screensaverNewAsteroidDelay
ssLastExistingAsteroid = -args.screensaverExistingAsteroidDelay
srcImgRect = srcImgSpwnPt + srcImgSz
resRect = (0, 0) + args.resolution

# Set argument defaults
if args.starsColour == None:
    args.starsColour = bgInvertedCol
if args.shipColour == None:
    args.shipColour = bgInvertedCol
if args.bulletsRange == None:
    args.bulletsRange = int(math.sqrt(math.pow(args.resolution[0], 2) + math.pow(args.resolution[1], 2)))
if args.megaBulletRange == None:
    args.megaBulletRange = args.bulletsRange * 3
if args.starsVolume == None:
    if args.backgroundColour == [0, 0, 0]:
        args.starsVolume = 0.00125
    else:
        args.starsVolume = 0

# Create font objects
try:
    smallFont = pygame.font.Font(args.textFont, args.textSmallSize)
    bigFont = pygame.font.Font(args.textFont, args.textBigSize)
except IOError:
    invalidFont = args.textFont
    args.textFont = pygame.font.get_default_font()
    clrTermLine()
    print 'Error: unable to load font file \'' + invalidFont + '\', using ' + args.textFont + ' instead'
    updTermLine('Loading game...')
    smallFont = pygame.font.Font(args.textFont, args.textSmallSize)
    bigFont = pygame.font.Font(args.textFont, args.textBigSize)

# Create background images
uBgImg = cv.CreateImage(srcImgSz, cv.IPL_DEPTH_8U, 3)
cv.Rectangle(uBgImg, (0, 0), srcImgSz, args.colourKey, cv.CV_FILLED)
bgImg = genBgImg()
oBgImg = pygame.Surface(args.resolution)
oBgImg.blit(bgImg, (0, 0))

# Create operation masks for cv.FloodFill()
maskImgSz = (srcImgSz[0] + 2, srcImgSz[1] + 2)
maskImg = cv.CreateImage(maskImgSz, cv.IPL_DEPTH_8U, 1)
cv.Rectangle(maskImg, (0, 0), maskImgSz, 0, cv.CV_FILLED)
bkMaskImg = cv.CreateImage(maskImgSz, cv.IPL_DEPTH_8U, 1) # Backup mask
cv.Rectangle(bkMaskImg, (0, 0), maskImgSz, 0, cv.CV_FILLED)

# Synchronize source image
if args.fillPos != None:
    genAsteroid(tuple(args.fillPos), 1, sync = 0)
    additionalRects = []
syncSrcImg(1)

# Create an untouched copy of source image to be used when restarting the game
origImg = cv.CreateImage(srcImgSz, cv.IPL_DEPTH_8U, 3)
cv.Copy(srcImgOCV, origImg)

# Get # of coloured pixels in source image for pixelsDetatched stat
if args.hideStats == 1 and (args.prankMode == 1 or args.screensaverMode == 1):
    srcImgColouredPixels = 1 # Speed up loading time when the variable is unneeded
else:
    srcImgColouredPixels = getColouredPixels(srcImgOCV)

# Create sprites and sprite groups
asteroids = pygame.sprite.RenderUpdates()
shipGrp = pygame.sprite.RenderUpdates()
bullets = pygame.sprite.RenderUpdates()
tempStaticText = pygame.sprite.RenderUpdates()
statsText = pygame.sprite.RenderUpdates()
FPSStateGrp = pygame.sprite.RenderUpdates()
updGroups = [asteroids, shipGrp, bullets]
if args.hideStats != 1:
    updGroups.append(statsText)
if args.displayFPS == 1:
    updGroups.append(FPSStateGrp)
groups = (asteroids, shipGrp, bullets, tempStaticText)
pauseTextObj = pauseText()
gameOverTextObj = gameOverText()
if args.prankMode != 1 and args.screensaverMode != 1:
    shipObj = ship()
    shipObj.mousePosChange(centerPt) # Rotate ship towards center
else:
    shipObj = None
cursorRectSpriteObj = cursorRectSprite()
statPixelsDetatchedObj = statPixelsDetatched()
statAsteroidsMadeObj = statAsteroidsMade()
statActiveAsteroidsObj = statActiveAsteroids()
FPSStateObj = FPSState()
mbStateObj = mbState()

# Make mouse cursor invisible in screensaver mode
if args.screensaverMode == 1:
    pygame.mouse.set_visible(0)

# Start game screen
if args.fullscreen == 1:
    winSrfc = pygame.display.set_mode(args.resolution, pygame.FULLSCREEN)
else:
    winSrfc = pygame.display.set_mode(args.resolution)

# Draw game
syncSrcImg(2, rect = resRect)
pygame.display.flip()

# Get exact display start time
displayStartTime = pygame.time.get_ticks()

# Clear terminal status line after completion
clrTermLine(1)

# Main game loop
while True:

    # Update time in milliseconds (ticks variable)
    updTicks()

    # Handle various game modes

    # Prank mode
    if args.prankMode == 1:

        # Handle events
        for event in pygame.event.get():

            # Event: key let go
            if event.type == pygame.locals.KEYUP:
                # Update latest characters typed
                if event.key < 256:
                    latestChrs.pop(0)
                    latestChrs.append(chr(event.key))
                if ''.join(latestChrs) == pmExitKw:
                    # Exit peacefully (user typed exit keyword)
                    gameExitSeq()

            # Event: mouse button pressed
            elif event.type == pygame.locals.MOUSEBUTTONDOWN:
                if srcImgSpwnPt[0] < event.pos[0] < srcImgSz[0] + srcImgSpwnPt[0] and srcImgSpwnPt[1] < event.pos[1] < srcImgSz[1] + srcImgSpwnPt[1]:
                    # Generate new asteroid if click is within source image area
                    genAsteroid((event.pos[0] - srcImgSpwnPt[0], event.pos[1] - srcImgSpwnPt[1]))

            # Event: mouse moved
            elif event.type == pygame.locals.MOUSEMOTION:
                # Update current mouse position
                mPos = event.pos

    # Screensaver mode
    elif args.screensaverMode == 1:

        # Handle events: exit on any mouse/keyboard event
        for event in pygame.event.get():
            if event.type in (pygame.locals.QUIT, pygame.locals.MOUSEMOTION, pygame.locals.MOUSEBUTTONUP, pygame.locals.MOUSEBUTTONDOWN, pygame.locals.KEYUP, pygame.locals.KEYDOWN) and ticks - displayStartTime > 1000:
                # Exit peacefully
                gameExitSeq()

        # New asteroid generation
        if ticksSecs - ssLastNewAsteroid > args.screensaverNewAsteroidDelay:
            # Time to generate random new asteroid
            genAsteroid((random.randrange(0, srcImgSz[0]), random.randrange(0, srcImgSz[1])))
            # Update ssLastNewAsteroid time
            ssLastNewAsteroid = ticksSecs

        # Existing asteroid destruction
        asteroidSprites = asteroids.sprites()
        if ticksSecs - ssLastExistingAsteroid > args.screensaverExistingAsteroidDelay and asteroidSprites != []:
            # Time to destroy random existing asteroid
            asteroidSprites[random.randrange(0, len(asteroidSprites))].nonJumpCpy.newAsteroids()
            # Update ssLastExistingAsteroid time
            ssLastExistingAsteroid = ticksSecs

    # Normal game mode
    else:

        # Handle events
        for event in pygame.event.get():

            # Event: window close button pressed
            if event.type == pygame.locals.QUIT:
                # Exit peacefully
                gameExitSeq()

            # Event: mouse button let go
            elif event.type == pygame.locals.MOUSEBUTTONUP:
                if event.button in (1, 3) and (ticksSecs - lastBulletShot) > args.bulletsDelay and paused == 0:
                    # Shoot bullet
                    curBullet = bullet()
                    lastBulletShot = ticksSecs
                    if event.button == 3:
                        # Generate new asteroid
                        curBullet.genAsteroid = event.pos

            # Event: mouse moved
            elif event.type == pygame.locals.MOUSEMOTION:
                # Update current mouse position
                mPos = event.pos

                # Rotate ship
                if shipObj.direction <= 2:
                    shipObj.mousePosChange(mPos)

            # Event: key pressed
            elif event.type == pygame.locals.KEYDOWN:
                if event.key in shipObj.mks[0] + shipObj.mks[1] + shipObj.mks[2] + shipObj.mks[3]:
                    # Deal with ship movement keys
                    # Add key to curMks, keep curMks length <= 2
                    if len(shipObj.curMks) == 2:
                        shipObj.curMks[1] = event.key
                    else:
                        shipObj.curMks.append(event.key)
                    # Update move direction
                    shipObj.updMoveDirection()

            # Event: key let go
            elif event.type == pygame.locals.KEYUP:
                if event.key in shipObj.mks[0] + shipObj.mks[1] + shipObj.mks[2] + shipObj.mks[3] and event.key in shipObj.curMks:
                    # Deal with ship movement keys
                    # Remove key from curMks
                    if event.key in shipObj.curMks:
                        shipObj.curMks.remove(event.key)
                    # Update move direction
                    shipObj.updMoveDirection()

                elif event.key == pygame.locals.K_ESCAPE:
                    # Exit peacefully
                    gameExitSeq()

                elif event.key == pygame.locals.K_r:
                    # Restart game
                    restartGame()

                elif event.key == pygame.locals.K_p and gameOverMode == 0:
                    # Pause/unpause game
                    if paused == 1:
                        # Unpause
                        paused = 0
                        if prePauseTime != None:
                            pauseTextObj.kill()
                            tempStaticText.clear(winSrfc, oBgImg)
                            pygame.display.update(tempStaticText.draw(winSrfc))
                            pausedFor = pygame.time.get_ticks() - prePauseTime
                            timeOffset -= pausedFor
                            FPSStateObj.lastUpdate -= pausedFor
                            updTicks()
                            shipObj.updMoveDirection()
                            prePauseTime = None
                    elif paused == 0:
                        # Pause
                        prePauseTime = pygame.time.get_ticks()
                        pauseTextObj.add(tempStaticText)
                        pygame.display.update(tempStaticText.draw(winSrfc))
                        paused = 1

                elif event.key == pygame.locals.K_t and paused == 0:
                    # Toggle show statistics
                    if statsText in updGroups:
                        # Toggle off
                        updGroups.remove(statsText)
                        # Clear text
                        statsText.clear(winSrfc, oBgImg)
                        for statObj in statsText.sprites():
                            pygame.display.update(statObj.rect)
                    else:
                        # Toggle on
                        updGroups.append(statsText)
                        # Draw updated stat values
                        for statObj in statsText.sprites():
                            statObj.drawText()

                elif event.key == pygame.locals.K_f:
                    # Toggle display FPS rate
                    if FPSStateGrp in updGroups:
                        # Toggle off
                        updGroups.remove(FPSStateGrp)
                        FPSStateGrp.clear(winSrfc, oBgImg)
                        pygame.display.update(FPSStateObj.rect)
                    else:
                        # Toggle on
                        updGroups.append(FPSStateGrp)

                elif event.key in (pygame.locals.K_c, pygame.locals.K_LSHIFT, pygame.locals.K_RSHIFT):
                    # Launch mega bullet if ready
                    if ticksSecs - mbStateObj.lastLaunch > args.megaBulletRechargeTime:
                        # Ready, so launch
                        launchMegaBullet()
                        # Update mega bullet state
                        mbStateObj.invisible()
                        mbStateObj.lastLaunch = ticksSecs
                    else:
                        # Not ready
                        pass

                elif event.key == pygame.locals.K_h:
                    # Save screenshot -> screenshot.png
                    try:
                        pygame.image.save(winSrfc, 'screenshot.png')
                        print 'Screenshot saved to screenshot.png.'
                    except pygame.error:
                        print 'Error: unable to save screenshot.png, check file permissions.'

        # Handle collisions if unpaused
        if paused == 0:

            # Check bullet (b) and asteroid (a) collision
            for a, b in pygame.sprite.groupcollide(asteroids, bullets, 0, 0).iteritems():
                # Get original copy of asteroid and bullet objects
                b = b[0].nonJumpCpy
                a = a.nonJumpCpy
                # Only make new asteroids if bullet doesn't have a set destination
                if b.genAsteroid == None:
                    # Make new asteroids
                    a.newAsteroids(b)
                    # Update active asteroids stat
                    changeAndRedrawStat(statActiveAsteroidsObj, statActiveAsteroidsObj.value - 1)
                    # Kill both objects
                    safeKillObj(b)
                    safeKillObj(a)

            # Check asteroids (a) and ship collisions (game over)
            # Only check collisions once per 0.125 seconds, mask collision checks are slow
            if lastGameOverChk + 125 < ticks:
                for a in pygame.sprite.spritecollide(shipObj, asteroids, 0):
                    if pygame.sprite.collide_mask(shipObj, a):
                        # Game over
                        gameOverTextObj.add(tempStaticText)
                        pygame.display.update(tempStaticText.draw(winSrfc))
                        paused = 1
                        gameOverMode = 1
                lastGameOverChk = ticks

    # Draw game if unpaused
    if paused == 0:

        # Update sprites
        for g in updGroups:
            g.update()
            g.clear(winSrfc, oBgImg)

        # Draw updated sprites
        [pygame.display.update(rects) for rects in additionalRects + [g.draw(winSrfc) for g in updGroups]]

        # Redraw mouse cursor if it has been overdrawn
        if args.screensaverMode != 1:
            cursorRectSpriteObj.rect.center = mPos
            for g in updGroups:
                if (pygame.sprite.spritecollide(cursorRectSpriteObj, g, 0) != []):
                    pygame.mouse.set_cursor(*cursor)
                    break

        # Reset additional rects list
        if additionalRects != []:
            # Only until near the end of coding the game I realised that a major drop in FPS (up to 1000%) was being caused by the fact that I misspelt 'additionalRects' in the line below, causing the loop to redraw extra areas that weren't necessary to redraw.
            additionalRects = []

    # Display FPS rate when paused
    if paused == 1 and FPSStateGrp in updGroups:
        FPSStateGrp.update()
        FPSStateGrp.clear(winSrfc, oBgImg)
        pygame.display.update(FPSStateGrp.draw(winSrfc))

    # Print FPS rate
    if args.printFPS == 1:
        updTermLine('FPS: ' + str(round(fpsClock.get_fps(), 2)))

    # Maintain FPS rate
    fpsClock.tick(fpsRate)

# "Sssssssssssssssssssssss..." (Real python language...)

# By Mustafa Al-Bassam
# Licence: Do whatever you want with it.
# ??-08-12
