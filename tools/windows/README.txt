Pacote Português - a content mod for Mad Television Tycoon
==========================================================

80 Portuguese films (1981-2005), with parody titles and names, their directors and cast, and pictures.
The pictures are AI-generated lookalikes, not stills from the films.

INSTALL
  1. Close the game.
  2. Extract this zip anywhere (right-click > Extract All...). Do not run it from inside the zip.
     Tip: to avoid Windows' security prompts, first right-click the zip > Properties > tick "Unblock" > OK,
     then extract.
  3. Double-click Install.bat.
     It finds the game through Steam. If it cannot, it asks for the game folder
     (in Steam: right-click the game > Manage > Browse local files), or drop that folder onto Install.bat.
     Windows may ask "The publisher could not be verified. Are you sure you want to run this software?"
     Click Run: batch files cannot carry a publisher signature, so Windows always says "Unknown Publisher".
     Install.bat and install.ps1 are plain text; open them in Notepad to see what they do.
     If Windows shows "Windows protected your PC", choose "More info" > "Run anyway".
     If the game folder is write-protected, it asks for administrator rights.
  4. Start a NEW game.

  Run Install.bat again after every game update (an update can add films and pictures of its own,
  which the mod's files must take in).
  To preview without changing anything: open a command prompt in this folder and run  Install.bat -DryRun

UNINSTALL
  Double-click Uninstall.bat. It removes only the files the installer wrote and that are unchanged.
  Keep this folder: the install record (install_record.json) is also saved here as a backup.

COMPATIBILITY
  The game loads one DATABASE\MOD\ItemsData.json and CastData.json, so this mod cannot be combined with
  other mods that write those files (for example name or translation database mods). The installer
  refuses to overwrite another mod's files.

WHAT IT CHANGES
  EXTERN\DATABASE\MOD\ItemsData.json, CastData.json   = the game's own files from your PC + this mod's entries
  EXTERN\DATABASE\MOD\pt_films_install.json           = install record (files written, with SHA-1)
  EXTERN\SCRN\<GENRE>\NNNN.png                         = 80 pictures, numbered after the game's own
  No game files are replaced. Steam "Verify integrity of game files" does not remove the mod files.
