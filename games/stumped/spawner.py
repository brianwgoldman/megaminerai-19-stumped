# Spawner: A resource spawner that generates branches or food.

# DO NOT MODIFY THIS FILE
# Never try to directly create an instance of this class, or modify its member variables.
# Instead, you should only be reading its variables and calling its functions.

from games.stumped.game_object import GameObject



class Spawner(GameObject):
    """The class representing the Spawner in the Stumped game.

    A resource spawner that generates branches or food.
    """

    def __init__(self):
        """Initializes a Spawner with basic logic as provided by the Creer code generator."""
        GameObject.__init__(self)

        # private attributes to hold the properties so they appear read only
        self._has_been_harvested = False
        self._health = 0
        self._tile = None
        self._type = ""

    @property
    def has_been_harvested(self):
        """True if this Spawner has been harvested this turn, and it will not heal at the end of the turn, False otherwise.

        :rtype: bool
        """
        return self._has_been_harvested

    @property
    def health(self):
        """How much health this Spawner has, which is used to calculate how much of its resource can be harvested.

        :rtype: int
        """
        return self._health

    @property
    def tile(self):
        """The Tile this Spawner is on.

        :rtype: Tile
        """
        return self._tile

    @property
    def type(self):
        """What type of resource this is ('food' or 'branches').

        :rtype: str
        """
        return self._type
