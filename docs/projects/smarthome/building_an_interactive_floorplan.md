---
tags:
  - WIP
  - smarthome
date: "2025-02-27"
title: Building An Interactive Floorplan in Home Assistant
---

# Background

I've recently decided to take a stab at setting up and improving some home automations via [Home Assistant](https://www.home-assistant.io/). After quickly setting up integration with a few smart lights around my unit, I found myself browsing Youtube for some inspiration. That was when I stumbled upon these fancy floorplan dashboards which allowed users to control lights while also updating a small 3d representation of the space. Immediately I knew I had 
to create something like that for my own place!

# Process

Luckily I was able to find quite a few tutorials around to get a good sense of how to accomplish something like this.

## Home, SweetHome3D

It all starts with a lovely piece of software called [SweetHome3D](https://www.sweethome3d.com/). SweetHome3D (I will refer to this as SH3D going forward) is an open source project focused on modelling homes, and comes with a plethora of 3D models out of the box. Additionally, more 3D asset libraries can be found [here](https://www.sweethome3d.com/importModels.jsp#ModelsLibraries). I really enjoyed the time spent in this software as it was fairly straight-forward to use, and came fairly feature packed. 

I started out with an extremely blurry and distorted image of my floorplan which I imported to SH3D and set a reference scale to based on the known dimensions of the unit (for me, I  didn't care for the measurements to be extremely exact and so this helped me get up-and-running much faster).

![Base plan](https://res.cloudinary.com/drwjkxxud/image/upload/v1740634902/unit_glghrv.png)

I traced the outlines to create the walls of the apartment and then marked each room area. From there I start adding in furniture and adjusting things as they go. I would avoid adding anything under the `Lights` tab for now as those will have an impact on the lighting in the render.

![Early model iteration](https://res.cloudinary.com/drwjkxxud/image/upload/v1740634444/Screenshot_2025-02-17_201455_jzj85o.png)

Some notes I had during this process was that I noticed when I tried to get too detailed with textures on furniture, floors and walls, that the end product started looking sloppy and tacky, to avoid this, I leveraged mostly out-of-box models without applied textures, and went in to modify any models that did have textures to just a basic colour scheme. This made it so renders came out (IMO) a lot smoother and pleasing to the eye. 

Once you've modelled out something you are happy with, it's time to add some lighting, here I go with primarily with the  `Halogen light` sources and a coloured source for the bedroom. I chose to avoid adding physical models for the lighting fixtures entirely as they introduce an additional source of light, however, if you want to do that without impacting your renders, you can set their light power to 0% and then add a light source in its place to have full control over it. Additionally I noted that there didn't seem to be any easy way to have custom light colours outside of the stock colour offerings. If that is desired I would suggest layering different colour light sources on top of each other and tweaking their strengths to achieve your desired lighting colour (i.e RGB-style).

Once you've added your lights in, it is time to start rendering. You want to pan around the model until you find an angle that you are happy with. Once you find that, right click on the 3D view and select `Store point of view`. We do this so that we can get back to that exact angle reference whenever we want which will be important for the renders as it is going to be a still frame where we overlay the light layers onto. Once you're ready, we can right click and enter the `Create a photo` menu. The following is the settings I used but these can be tweaked to your liking.

```
- Quality: best
- Add ceiling lights: false
- Renderer: Sunflow
- Date: 05/22
- Time: 8:22 PM
```

I would create the first render with all lights turned off (you can toggle their visibility in the furniture sidebar). For subsequent renders, I would toggle one light source on (or one group, depending on how you want to manage your smart lights) and toggle everything else off and create another render. 

Another thing to note is when creating the renders, the time of day plays a big role in the outcome of the render (assuming you are including lighting into the renders). I found that sunset was the ideal time of day to set the render to (this will vary depending on the date you've selected as well). Rendering at night time made the lighting contrast too much with the interior. I also tried renders in the morning and those came out nicely as well - I just went with sunset for personal preference.

![First render](https://res.cloudinary.com/drwjkxxud/image/upload/v1740634575/home-bedroom_uxmydy.png)

## Cropping the Light Layers

Next I loaded up the light layer renders into GIMP (you can use any photo editor of your choosing that supports transparency) and started cropping out each room/section illuminated by light. By the end of this you should have a working prototype of the floorplan that you can toggle the lights on based on their layer visibility. For my example, this took a lot more time and effort since there were a lot of areas that overlapped (den, foyer, living room, kitchen). This is a bit more tricky as light bleeds out in various areas that we need to crop and account for as well, if you have doors properly segmenting all these areas, this should be no issue at all.

## Configuring Home Assistant

Once all the images are rendered and cropped, we are ready to put it all together in Home Assistant.

```
type: picture-elements
# Base image layer, all lights off
image: local/images/floorplan/home.png
elements:
	# Kitchen lights image layer
  - type: image
    entity: light.kitchen
    state_image:
      "on": local/images/floorplan/kitchen_on.png
      "off": local/images/floorplan/transparent.png
    style:
      left: 50%
      top: 50%
      width: 100%
  # Icon to allow us to toggle state from image card
  # Ensure these are added at the bottom (top-most layer), otherwise other layers may cover it
  - type: state-icon
    entity: light.kitchen
    style:
      left: 35%
      top: 50%
    tap_action:
      action: toggle
```

## Results

Anddd... voila! After adding a few more lights to the configuration, I ended up with something like this:

![Floorplan](https://res.cloudinary.com/drwjkxxud/image/upload/v1740711754/ezgif-648ae16309c97c_slxemr.gif)

# References

- [A handy video guide that encapsulates everything covered here](https://www.youtube.com/watch?v=9p9PBtM0O8Q)
