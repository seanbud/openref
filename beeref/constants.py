# This file is part of BeeRef.
#
# BeeRef is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# BeeRef is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with BeeRef.  If not, see <https://www.gnu.org/licenses/>.

APPNAME = 'OpenRef'
APPNAME_FULL = f'{APPNAME} Reference Canvas'
VERSION = '0.4.0b2'
WEBSITE = 'https://github.com/seanbud/openref'
COPYRIGHT = ('OpenRef © 2026 Sean Budning · '
             'BeeRef © 2021-2024 Rebecca Breu')

CHANGED_SYMBOL = '✎'

COLORS = {
    # Qt:
    'Active:Base': (60, 60, 60),
    'Active:AlternateBase': (70, 70, 70),
    'Active:Window': (31, 31, 31),
    'Active:Button': (53, 53, 53),
    'Active:Text': (232, 233, 237),
    'Active:HighlightedText': (255, 255, 255),
    'Active:WindowText': (200, 200, 200),
    'Active:ButtonText': (200, 200, 200),
    'Active:Highlight': (8, 150, 194),
    'Active:Link': (22, 169, 216),

    'Disabled:Base': (40, 40, 40),
    'Disabled:Window': (40, 40, 40, 50),
    'Disabled:WindowText': (120, 120, 120),
    'Disabled:Light': (0, 0, 0, 0),
    'Disabled:Text': (140, 140, 140),

    # OpenRef specific:
    'Scene:Selection': (103, 224, 220),
    'Scene:Canvas': (24, 24, 24),
    'Scene:Text': (232, 233, 237),
}
