# UWP-DOOMdumper

Allows modding game files in the UWP/Game Pass version of DOOM Eternal.  

This is an automated tool that allows the user to choose a new installation directory to sideload DOOM Eternal from.
The game will be copied there before being uninstalled from the original location. This allows full control over   
the game directory, for modding.

This tool uses UWPInjector/UWPDumper to dump the game to a new location, while it is running.  
Therefore, UWP-DEdumper **requires** the [UWPDumper](https://github.com/Wunkolo/UWPDumper) binaries.

Also requires a zip file name `EternalModInjector-UWP.zip` to be in the current directory
