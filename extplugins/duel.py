#
# BigBrotherBot(B3) (www.bigbrotherbot.net)
# Copyright (C) 2010 Courgette
# 
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
#
# CHANGELOG
#     2010/08/28 - 1.0 - Courgette
#    * create plugin based on 1989trouble07's suggestion on the B3 forums
#
#     2010/09/14 - 1.1 - Courgette
#    * handle player disconnection
#

__author__  = 'Courgette'
__version__ = '1.1'


import b3
import b3.events
import b3.plugin


class DuelPlugin(b3.plugin.Plugin):
    requiresConfigFile = False
    _adminPlugin = None

    def onStartup(self):
        self._adminPlugin = self.console.getPlugin('admin')
        if not self._adminPlugin:
            return False

        self.registerEvent(b3.events.EVT_CLIENT_KILL)
        self.registerEvent(b3.events.EVT_CLIENT_DISCONNECT)
        self.registerEvent(b3.events.EVT_GAME_ROUND_END)
        
        self._adminPlugin.registerCommand(self, 'duel', 1, self.cmd_duel)
        self._adminPlugin.registerCommand(self, 'duelreset', 1, self.cmd_duelreset)
        self._adminPlugin.registerCommand(self, 'duelcancel', 1, self.cmd_duelcancel)


    def onEvent(self, event):
        """\
        Handle intercepted events
        """
        if event.type == b3.events.EVT_CLIENT_KILL and event.client and event.client.isvar(self, 'duelling'):
            duels = event.client.var(self, 'duelling', {}).value
            for duel in duels.values():
                duel.registerKillEvent(event)
        elif event.type == b3.events.EVT_CLIENT_DISCONNECT:
            self.onDisconnect(event)
        elif event.type == b3.events.EVT_GAME_ROUND_END:
            for c in self.console.clients.getList():
                if c.isvar(self, 'duelling'):
                    self._showDuelsScoresToPlayer(c)
                    
    def onDisconnect(self, event):
        """\
        Handle client disconnection
        """
        self.debug('client disconnecting : %r' % event.client)
        for c in self.console.clients.getList():
            duels = event.client.var(self, 'duelling', {}).value
            for duel in duels.values():
                if duel._clientA == event.client or duel._clientB == event.client:
                    duel.announceScoreTo(duel._clientA)
                    duel.announceScoreTo(duel._clientB)
                    self._cancelDuel(duel)
        duels = event.client.var(self, 'duelling', {}).value
        for duel in duels.values():
            duel.announceScoreTo(duel._clientA)
            duel.announceScoreTo(duel._clientB)
            self._cancelDuel(duel)

    def cmd_duelcancel(self, data, client, cmd=None):
        """\
        [<name>] - cancel a duel you started
        """
        duels = client.var(self, 'duelling', {}).value
        if len(duels) == 0:
            client.message('you started no duel. Nothing to cancel')
            return
        # this will split the player name and the message
        input = self._adminPlugin.parseUserCmd(data)
        if not input:
            if len(duels) == 1:
                self._cancelDuel(duels.values()[0])
            else:
                client.message('^7you have %s duels running, type !duelcancel <name>' % len(duels))
        else:
            # input[0] is the player you challenge
            opponent = self._adminPlugin.findClientPrompt(input[0], client)
            if not opponent:
                # a player matching the name was not found, a list of closest matches will be displayed
                # we can exit here and the user will retry with a more specific player
                return
            if opponent not in duels:
                client.message('^7You have no duel with %s, cannot cancel' % opponent.exactName)
            else:
                self._cancelDuel(duels[opponent])
                
    def cmd_duelreset(self, data, client, cmd=None):
        """\
        [<name>] - reset scores for a duel you started
        """
        duels = client.var(self, 'duelling', {}).value
        if len(duels) == 0:
            client.message('you started no duel. Nothing to reset')
            return
        # this will split the player name and the message
        input = self._adminPlugin.parseUserCmd(data)
        if not input:
            if len(duels) == 1:
                duels.values()[0].resetScores()
            else:
                client.message('^7you have %s duels running, type !duelreset <name>' % len(duels))
        else:
            # input[0] is the player you challenge
            opponent = self._adminPlugin.findClientPrompt(input[0], client)
            if not opponent:
                # a player matching the name was not found, a list of closest matches will be displayed
                # we can exit here and the user will retry with a more specific player
                return
            if opponent not in duels:
                client.message('^7You have no duel with %s, cannot reset' % opponent.exactName)
            else:
                duels[opponent].resetScores()
                
        
    def cmd_duel(self, data, client, cmd=None):
        """\
        <name> - challenge a player for a duel or accept a duel
        """
        # this will split the player name and the message
        input = self._adminPlugin.parseUserCmd(data)
        if not input:
            client.message('^7Invalid data, try !help duel')
            return False
        else:
            # input[0] is the player you challenge
            opponent = self._adminPlugin.findClientPrompt(input[0], client)
            if not opponent:
                # a player matching the name was not found, a list of closest matches will be displayed
                # we can exit here and the user will retry with a more specific player
                return False
        # from now on, opponent if the player event.client challenges
        if client == opponent:
            client.message('you cannot duel yourself')
            return
        client_duels = client.var(self, 'duelling', {}).value
        opponent_duels = opponent.var(self, 'duelling', {}).value
        if client not in opponent_duels and opponent not in client_duels:
            # no duel exists between those two
            # creating duel
            client_duels[opponent] = Duel(client, opponent)
            client.message('duel proposed to %s' % opponent.exactName)
        elif client in opponent_duels:
            # we are accepting a duel
            duel = opponent_duels[client]
            duel.acceptDuel()
            client_duels[opponent] = duel
        elif opponent in client_duels:
            # duel already exists but only on our side
            duel = client_duels[opponent]
            client.message('^7you suggested a duel to %s' % opponent.exactName)
            opponent.message('%s^7 is challenging you in a duel. Type !duel %s to start duelling' % (client.exactName, client.name))
        
    def _showDuelsScoresToPlayer(self, player):
        duels = player.var(self, 'duelling', {}).value
        for duel in duels.values():
            duel.announceScoreTo(player)

    def _cancelDuel(self, duel):
        """will remove references to this duel in both players' instances"""
        self.debug('canceling duel %r' % duel)
        clientA = duel._clientA
        clientB = duel._clientB
        if clientA:
            try:
                duelsA = clientA.var(self, 'duelling', {}).value
                del duelsA[clientB]
                self.debug('removed ref to duel %s from player %s' % (id(duel), clientA.name))
                clientA.message('^7duel with %s^7 canceled' % clientB.exactName)
            except KeyError: pass
        if clientB:
            try:
                duelsB = clientB.var(self, 'duelling', {}).value
                del duelsB[clientA]
                self.debug('removed ref to duel %s from player %s' % (id(duel), clientB.name))
                clientB.message('^7duel with %s^7 canceled' % clientA.exactName)
            except KeyError: pass
            
class Duel(object):
    """ How does it work ?
    
    player A challenges player B
        player B is notified
    player B accept challenge from player A
        players A and B get notified that the duel stated
        
    on each kill of player A or B
        players A and B get notified of the current duel score
        
    on round end
        players A and B get notified of the duel score
        players A and B get reminded to type duelreset to set scores back to 0
    
    on player A or B disconnection
        the other player get notified of the duel score
        
    """
    STATUS_WAITING_AGREEMENT = 0 # challenge proposed, waiting for agreement
    STATUS_STARTED = 1 # both players agreed to duel
    _status = STATUS_WAITING_AGREEMENT
    _clientA = None # the player who propose the duel
    _clientB = None # the player who accept the duel
    _scores = {}
    
    def __init__(self, clientA, clientB):
        if not isinstance(clientA, b3.clients.Client):
            raise DuelError('clientA is not a client')
        if not isinstance(clientB, b3.clients.Client):
            raise DuelError('opponent is not a client')
        if not clientA.connected:
            raise DuelError('clientA is not connected')
        if not clientB.connected:
            raise DuelError('opponent is not connected')
        if clientA == clientB:
            raise DuelError('you cannot challenge yourself')
        self._clientA = clientA
        self._clientB = clientB
        self._scores = {clientA: 0, clientB: 0}
        self._clientB.message('%s proposes a duel. To accept type !duel %s' % (self._clientA.exactName, self._clientA.name.lower()))
        print "creating duel between clients %r and %r" % (clientA, clientB)
    
    def acceptDuel(self):
        self._status = Duel.STATUS_STARTED
        self._clientA.message('%s^7 is now duelling with you' % self._clientB.exactName)
        self._clientB.message('^7You accepted %s^7\'s duel' % self._clientA.exactName)
        self.resetScores()
    
    def resetScores(self):
        self._scores = {self._clientA: 0, self._clientB: 0}
        self.announceScoreTo(self._clientA)
        self.announceScoreTo(self._clientB)
        
    def registerKillEvent(self, kill_event):
        if self._status == Duel.STATUS_WAITING_AGREEMENT:
            return
        if not isinstance(kill_event, b3.events.Event):
            raise DuelError('invalid killer')
        killer = kill_event.client
        victim = kill_event.target
        if killer == self._clientA and self._clientB == victim \
        or killer == self._clientB and self._clientA == victim:
            self._scores[killer] += 1
            self.announceScoreTo(killer)
            self.announceScoreTo(victim)
            
    def announceScoreTo(self, player):
        if self._status == Duel.STATUS_WAITING_AGREEMENT:
            return
        msg = "^5Duel: ^7%(player)s %(playerScore)s^5:%(opponentScore)s ^7%(opponent)s"
        opponent = player == self._clientA and self._clientB or self._clientA
        scorePlayer = self._scores[player]
        scoreOpponent = self._scores[opponent]
        colorPlayer = colorOpponent = '^5' # neutral color
        if scorePlayer > scoreOpponent:
            colorPlayer = '^2'
            colorOpponent = '^1'
        else:
            colorPlayer = '^1'
            colorOpponent = '^2'
        player.message(msg % {
                              'player': player.exactName,
                              'opponent': opponent.exactName, 
                              'playerScore': '%s%s' % (colorPlayer, scorePlayer), 
                              'opponentScore': '%s%s' % (colorOpponent, scoreOpponent), 
                              })
    
class DuelError(Exception): pass   


if __name__ == '__main__':
    from b3.fake import fakeConsole
    from b3.fake import joe, simon, moderator, superadmin
    import time
    
    p = DuelPlugin(fakeConsole)
    p.onStartup()
    
    """
    joe._exactName="^4J^5o^3e"
    joe.connects(cid=1)
    joe.says("!duel")
    joe.says("!duel nonexistingplayer")
    joe.says('!duelreset')
    joe.says('!duelcancel')
    joe.says('!duelreset jesus')
    joe.says('!duelcancel jesus')
    print "-------------------------"
    
    simon._exactName="^1Sim^3on"
    simon.connects(cid=2)
    simon.groupBits = 1
    joe.says('!duel simo')
    joe.says('!duelreset')
    joe.says('!duelcancel')
    joe.says('!duelreset jesus')
    joe.says('!duelcancel jesus')
    print "-------------------------"
    
    joe.says('!duel simo')
    simon.says('!duel jo')

    superadmin.connects(cid=5)
    simon.says('!duel god')
    superadmin.says('!duel simon')
    
    moderator.connects(cid=3)
    simon.kills(joe)
    simon.kills(superadmin)
    simon.kills(moderator)
    simon.kills(joe)
    simon.kills(moderator)
    moderator.kills(joe)
    print "-------------------------"
    
    joe.kills(moderator)
    joe.kills(superadmin)
    joe.kills(simon)
    moderator.kills(joe)
    print "-------------------------"
    
    fakeConsole.queueEvent(b3.events.Event(b3.events.EVT_GAME_ROUND_END, None, None))
    time.sleep(5)
    print "-------------------------"

    joe.says('!duelcancel')
    moderator.kills(joe)
    moderator.kills(simon)
    print "-------------------------"
    
    joe.says('!duelreset')
    simon.kills(moderator)
    simon.kills(moderator)
    simon.kills(moderator)
    moderator.kills(joe)
    """
    
    joe.connects(cid=1)
    simon.connects(cid=2)
    simon.groupBits = 1
    joe.says('!duel simon')
    simon.says('!duel joe')
    time.sleep(1)
    joe.disconnects()

    while True: time.sleep(1)
    