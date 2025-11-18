library(ggplot2)
library(tidyverse)

cne_pitching <- map_dfr(
  .x = cne_ids$team_id,
  .f = ~ ncaa_2025_stats(.x)
)

cne_pitching_team_totals<- cne_pitching|>
  mutate(across(7:38, ~ replace_na(., 0)))|>
  mutate(across(7:38, as.numeric),
         AB = bf - (bb + hb + ibb + sha + sfa),
         BAA = h/AB,
         flyout_perc = fo / (go + fo),
         groundout_perc = go / (go + fo),
         k_perc = so / (bf),
         bb_perc = bb / bf,
         obp = (h + bb + hb) / (AB + bb + hb + sfa),
         x1b_a = h - (x2b_a + x3b_a + hr_a),
         ops = (x1b_a + 2*x2b_a + 3*x3b_a + 4*hr_a)/AB)|>
  arrange(desc(ip))|>
  filter(player == "Totals")|>
  distinct(team_id, .keep_all = TRUE)



cne_pitching_stats <- cne_pitching |>
  filter(number != "-", nchar(number) <= 2) |>
  mutate(
    # Convert IP from "x.y" (e.g., 5.2) to fractional innings
    ip_numeric = floor(ip) + (ip - floor(ip)) * 10 / 3
  ) |>
  group_by(team_id) |>
  summarize(
    # Totals
    total_er = sum(er, na.rm = TRUE),
    total_innings = sum(ip_numeric, na.rm = TRUE),
    k = sum(so, na.rm = TRUE),
    bf_total = sum(bf, na.rm = TRUE),
    bb_total = sum(bb, na.rm = TRUE),
    hb_total = sum(hb, na.rm = TRUE),
    ibb_total = sum(ibb, na.rm = TRUE),
    sha_total = sum(sha, na.rm = TRUE),
    sfa_total = sum(sfa, na.rm = TRUE),
    h_total = sum(h, na.rm = TRUE),
    x2b_total = sum(x2b_a, na.rm = TRUE),
    x3b_total = sum(x3b_a, na.rm = TRUE),
    hr_total = sum(hr_a, na.rm = TRUE),
    fo_total = sum(fo, na.rm = TRUE),
    go_total = sum(go, na.rm = TRUE),
    
    # Derived statistics
    AB = bf_total - (bb_total + hb_total + ibb_total + sha_total + sfa_total),
    BAA = h_total / AB,
    flyout_perc = fo_total / (go_total + fo_total),
    groundout_perc = go_total / (go_total + fo_total),
    k_perc = k / bf_total,
    bb_perc = bb_total / bf_total,
    obp = (h_total + bb_total + hb_total) / (AB + bb_total + hb_total + sfa_total),
    x1b_a = h_total - (x2b_total + x3b_total + hr_total),
    ops = (x1b_a + 2*x2b_total + 3*x3b_total + 4*hr_total + obp)/ AB,
    k_bb_ratio = k/bb_total,
    
    # ERA
    era = (total_er * 9) / total_innings
  )|>
  inner_join(cne_ids, by = c("team_id"))


gordon_pitching <- conference_pitching_stats_|>
  filter(team_id == 597109)

wne_pitching <- conference_pitching_stats_|>
  filter(team_id == 597070)

roger_pitching <- conference_pitching_stats_|>
  filter(team_id == 597017)

hartford_pitching <- conference_pitching_stats_|>
  filter(team_id == 596977)

write.csv(hartford_pitching, "hartford_pitching.csv")
write.csv(roger_pitching, "rogerwilliams_pitching.csv")
write.csv(wne_pitching, "wne_pitching.csv")
write.csv(gordon_pitching, "gordon_pitching.csv")
