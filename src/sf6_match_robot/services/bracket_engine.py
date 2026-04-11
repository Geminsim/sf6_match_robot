import math
import random
from typing import List, Dict

from sf6_match_robot.models.tournament import MatchData

class BracketEngine:
    """Generates and manages double-elimination brackets."""

    @staticmethod
    def generate_seeds(participants: List[int]) -> List[int]:
        """Randomly shuffle participants and assign seed numbers.
        Returns a list of participant user_ids. Index 0 is seed 1, Index 1 is seed 2, etc.
        """
        shuffled = participants.copy()
        random.shuffle(shuffled)
        return shuffled

    @staticmethod
    def seed_order(bracket_size: int) -> List[int]:
        """Generate standard tournament seeding order."""
        if bracket_size == 1:
            return [1]
        half = BracketEngine.seed_order(bracket_size // 2)
        return [
            val for pair in [(s, bracket_size + 1 - s) for s in half]
            for val in pair
        ]

    @staticmethod
    def generate_bracket(tournament_id: int, participants: List[int]) -> List[MatchData]:
        """Given a list of user IDs (already shuffled), generate all matches."""
        n = len(participants)
        if n < 2:
            raise ValueError("At least 2 participants are required.")
            
        bracket_size = 2 ** math.ceil(math.log2(n))
        matches: List[MatchData] = []
        
        # Determine number of Winners Bracket rounds
        wb_rounds = int(math.log2(bracket_size))
        
        # --- Generate Winners Bracket ---
        # First, generate the empty matches structure
        wb_matches: Dict[int, List[MatchData]] = {} # round_num -> list of MatchData
        
        # Create WB R1 matches, applying byes.
        order = BracketEngine.seed_order(bracket_size)
        r1_matches = []
        match_counter = 1
        
        # participant list is 0-indexed where index is seed-1
        # e.g. seed 1 -> participants[0]
        for i in range(0, len(order), 2):
            s1 = order[i]
            s2 = order[i+1]
            
            p1 = participants[s1 - 1] if s1 <= n else None
            p2 = participants[s2 - 1] if s2 <= n else None
            
            status = 'pending'
            if p1 and p2:
                status = 'ready'
            elif p1 or p2:
                status = 'completed' # Bye match
                
            match = MatchData(
                tournament_id=tournament_id,
                match_tag=f"WB-R1-M{match_counter}",
                bracket='winners',
                round_num=1,
                match_num=match_counter,
                player1_id=p1,
                player2_id=p2,
                status=status,
                winner_id=p1 if p1 and not p2 else p2 if p2 and not p1 else None,
            )
            r1_matches.append(match)
            matches.append(match)
            match_counter += 1
            
        wb_matches[1] = r1_matches
        
        # Create subsequent WB rounds
        for r in range(2, wb_rounds + 1):
            r_matches = []
            prev_round_matches = wb_matches[r-1]
            num_matches_this_round = len(prev_round_matches) // 2
            
            for m in range(1, num_matches_this_round + 1):
                match = MatchData(
                    tournament_id=tournament_id,
                    match_tag=f"WB-R{r}-M{m}",
                    bracket='winners',
                    round_num=r,
                    match_num=m,
                )
                r_matches.append(match)
                matches.append(match)
                
                # Link previous round matches to this round
                m1 = prev_round_matches[(m-1)*2]
                m2 = prev_round_matches[(m-1)*2 + 1]
                
                m1.next_winner_match = match.match_tag
                m1.next_winner_slot = 1
                
                m2.next_winner_match = match.match_tag
                m2.next_winner_slot = 2
                
            wb_matches[r] = r_matches
            
        # Push byes forward (auto-advance)
        for r in range(1, wb_rounds):
            for i, match in enumerate(wb_matches[r]):
                if match.status == 'completed' and match.winner_id: # it was a bye
                    # advance to next round
                    next_m = next((m for m in wb_matches[r+1] if m.match_tag == match.next_winner_match), None)
                    if next_m:
                        if match.next_winner_slot == 1:
                            next_m.player1_id = match.winner_id
                        else:
                            next_m.player2_id = match.winner_id
                            
                        if next_m.player1_id and next_m.player2_id:
                            if next_m.player1_id == -1 or next_m.player2_id == -1:
                                BracketEngine._resolve_lb_byes(next_m, matches)
                            else:
                                next_m.status = 'ready'

        # --- Generate Losers Bracket ---
        # The LB alternates between drop-down rounds (receiving WB losers) and reduction rounds.
        if n > 2:
            lb_matches: Dict[int, List[MatchData]] = {}
            lb_rounds = 2 * (wb_rounds - 1)
            
            for r in range(1, lb_rounds + 1):
                r_matches = []
                
                if r == 1:
                    # LB R1: WB R1 losers vs each other
                    num_matches = len(wb_matches[1]) // 2
                    for m in range(1, num_matches + 1):
                        match = MatchData(
                            tournament_id=tournament_id,
                            match_tag=f"LB-R1-M{m}",
                            bracket='losers',
                            round_num=1,
                            match_num=m
                        )
                        r_matches.append(match)
                        matches.append(match)
                        
                        wb_m1 = wb_matches[1][(m-1)*2]
                        wb_m2 = wb_matches[1][(m-1)*2 + 1]
                        
                        wb_m1.next_loser_match = match.match_tag
                        wb_m1.next_loser_slot = 1
                        
                        wb_m2.next_loser_match = match.match_tag
                        wb_m2.next_loser_slot = 2
                        
                elif r % 2 == 0:
                    # Drop-down round: LB winners vs WB losers
                    # The WB round dropping down is r/2 + 1
                    wb_round_dropping = r // 2 + 1
                    wb_losers = wb_matches[wb_round_dropping]
                    prev_lb = lb_matches[r-1]
                    
                    num_matches = len(wb_losers)
                    for m in range(1, num_matches + 1):
                        match = MatchData(
                            tournament_id=tournament_id,
                            match_tag=f"LB-R{r}-M{m}",
                            bracket='losers',
                            round_num=r,
                            match_num=m
                        )
                        r_matches.append(match)
                        matches.append(match)
                        
                        # Link WB dropping
                        wb_m = wb_losers[num_matches - m] # Cross matching (simplified reverse)
                        wb_m.next_loser_match = match.match_tag
                        wb_m.next_loser_slot = 2
                        
                        # Link prev LB winner
                        lb_m = prev_lb[m-1]
                        lb_m.next_winner_match = match.match_tag
                        lb_m.next_winner_slot = 1

                else:
                    # Reduction round: LB players vs each other
                    prev_lb = lb_matches[r-1]
                    num_matches = len(prev_lb) // 2
                    
                    for m in range(1, num_matches + 1):
                        match = MatchData(
                            tournament_id=tournament_id,
                            match_tag=f"LB-R{r}-M{m}",
                            bracket='losers',
                            round_num=r,
                            match_num=m
                        )
                        r_matches.append(match)
                        matches.append(match)
                        
                        lb_m1 = prev_lb[(m-1)*2]
                        lb_m2 = prev_lb[(m-1)*2 + 1]
                        
                        lb_m1.next_winner_match = match.match_tag
                        lb_m1.next_winner_slot = 1
                        
                        lb_m2.next_winner_match = match.match_tag
                        lb_m2.next_winner_slot = 2

                lb_matches[r] = r_matches
                
            # Process Byes dropping into LB
            # If a WB R1 match had a BYE, no loser drops to LB. 
            # In LB R1, logic is tricky, simple version: auto-advance if slot empty because of bye
            for wb_r1_match in wb_matches[1]:
                if wb_r1_match.status == 'completed' and wb_r1_match.next_loser_match:
                    # It was a bye, so there is no loser. The slot in LB should be filled with "BYE"
                    # But the algorithm will just treat it as a missing player. 
                    lb_dest = next((m for m in matches if m.match_tag == wb_r1_match.next_loser_match), None)
                    if lb_dest:
                        if wb_r1_match.next_loser_slot == 1:
                            lb_dest.player1_id = -1 
                        else:
                            lb_dest.player2_id = -1
                            
                        BracketEngine._resolve_lb_byes(lb_dest, matches)
                        
        else:
            lb_matches = {}

        # --- Grand Finals ---
        gf1 = MatchData(
            tournament_id=tournament_id,
            match_tag="GF-1",
            bracket='grand_finals',
            round_num=1,
            match_num=1
        )
        matches.append(gf1)
        
        gf2 = MatchData(
            tournament_id=tournament_id,
            match_tag="GF-2",
            bracket='grand_finals',
            round_num=2,
            match_num=1
        )
        matches.append(gf2)
        
        # Link WB Finals
        wb_final = wb_matches[wb_rounds][0]
        wb_final.next_winner_match = gf1.match_tag
        wb_final.next_winner_slot = 1
        
        if n > 2:
            lb_final = lb_matches[lb_rounds][0]
            lb_final.next_winner_match = gf1.match_tag
            lb_final.next_winner_slot = 2
        else:
            wb_final.next_loser_match = gf1.match_tag
            wb_final.next_loser_slot = 2
            
        gf1.next_loser_match = gf2.match_tag # if LB wins GF1, WB drops to GF2
        gf1.next_loser_slot = 1 
        gf1.next_winner_match = gf2.match_tag # if LB wins GF1, LB advances to GF2
        gf1.next_winner_slot = 2

        return matches

    @staticmethod
    def _resolve_lb_byes(match: MatchData, all_matches: List[MatchData]) -> List[str]:
        ready_matches = []
        if match.player1_id == -1 and match.player2_id == -1:
            match.status = 'completed'
            match.winner_id = -1 
        elif match.player1_id == -1 and match.player2_id is not None:
            match.status = 'completed'
            match.winner_id = match.player2_id
        elif match.player2_id == -1 and match.player1_id is not None:
            match.status = 'completed'
            match.winner_id = match.player1_id
            
        if match.status == 'completed' and match.winner_id:
            if match.next_winner_match:
                next_m = next((m for m in all_matches if m.match_tag == match.next_winner_match), None)
                if next_m:
                    if match.next_winner_slot == 1:
                        next_m.player1_id = match.winner_id
                    else:
                        next_m.player2_id = match.winner_id
                        
                    if next_m.player1_id and next_m.player2_id:
                        if next_m.player1_id == -1 or next_m.player2_id == -1:
                             ready_matches.extend(BracketEngine._resolve_lb_byes(next_m, all_matches))
                        else:
                             next_m.status = 'ready'
                             ready_matches.append(next_m.match_tag)
        return ready_matches

    @staticmethod
    def advance_winner(all_matches: List[MatchData], completed_match_tag: str) -> List[str]:
        """Process a completed match: advance winner, drop loser.
        Returns list of match_tags that became READY as a result.
        """
        ready_matches = []
        completed_match = next((m for m in all_matches if m.match_tag == completed_match_tag), None)
        if not completed_match or completed_match.status != 'completed':
            return []
            
        winner_id = completed_match.winner_id
        loser_id = completed_match.loser_id

        # Advance Winner
        if completed_match.match_tag == "GF-1" and winner_id == completed_match.player1_id:
            # Player 1 is WB Champ. GF-2 not needed.
            gf2 = next((m for m in all_matches if m.match_tag == "GF-2"), None)
            if gf2:
                gf2.status = 'completed' # basically cancelled/bypassed
                gf2.winner_id = completed_match.player1_id
            return [] # Tournament is over, cancel loser drop to GF-2

        if completed_match.next_winner_match and winner_id:
            next_m = next((m for m in all_matches if m.match_tag == completed_match.next_winner_match), None)
            if next_m:
                if completed_match.next_winner_slot == 1:
                    next_m.player1_id = winner_id
                else:
                    next_m.player2_id = winner_id
                    
                if next_m.player1_id and next_m.player2_id and next_m.player1_id != -1 and next_m.player2_id != -1:
                    next_m.status = 'ready'
                    ready_matches.append(next_m.match_tag)

        # Drop Loser
        if completed_match.next_loser_match and loser_id:
            next_m = next((m for m in all_matches if m.match_tag == completed_match.next_loser_match), None)
            if next_m:
                if completed_match.next_loser_slot == 1:
                    next_m.player1_id = loser_id
                else:
                    next_m.player2_id = loser_id
                    
                if next_m.player1_id and next_m.player2_id:
                     if next_m.player1_id == -1 or next_m.player2_id == -1:
                         ready_matches.extend(BracketEngine._resolve_lb_byes(next_m, all_matches))
                     else:
                        next_m.status = 'ready'
                        ready_matches.append(next_m.match_tag)

        return ready_matches

    @staticmethod
    def calculate_placements(matches: List[MatchData]) -> Dict[int, int]:
        """Calculate final placements (1st through 8th) from completed bracket."""
        scores = {}
        
        champion_id = None
        gf2 = next((m for m in matches if m.match_tag == "GF-2"), None)
        gf1 = next((m for m in matches if m.match_tag == "GF-1"), None)
        
        if gf2 and gf2.status == 'completed' and gf2.winner_id:
            champion_id = gf2.winner_id
        elif gf1 and gf1.status == 'completed' and gf1.winner_id:
            champion_id = gf1.winner_id
            
        if champion_id and champion_id != -1:
            scores[champion_id] = float('inf')
            
        for m in matches:
            if m.status == 'completed' and m.bracket in ['losers', 'grand_finals']:
                if m.loser_id and m.loser_id != -1:
                    score = m.round_num if m.bracket == 'losers' else 10000
                    scores[m.loser_id] = score
                    
        from collections import defaultdict
        score_groups = defaultdict(list)
        for pid, sc in scores.items():
            score_groups[sc].append(pid)
            
        placements = {}
        current_rank = 1
        for sc in sorted(score_groups.keys(), reverse=True):
            group = score_groups[sc]
            for pid in group:
                placements[pid] = current_rank
            current_rank += len(group)
            
        return placements

    @staticmethod
    def is_tournament_complete(matches: List[MatchData]) -> bool:
        """Check if the tournament has a champion."""
        gf1 = next((m for m in matches if m.match_tag == "GF-1"), None)
        gf2 = next((m for m in matches if m.match_tag == "GF-2"), None)
        
        if gf1 and gf1.status == 'completed':
            if gf1.winner_id == gf1.player1_id: # WB Champ won
                return True
            if gf2 and gf2.status == 'completed':
                return True
                
        return False
