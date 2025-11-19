library(rvest)
library(dplyr)
library(tidyr)
library(glue)
library(janitor)
library(purrr)
library(collegebaseball)

ncaa_2025_stats <- function(team_id, year = 2025, type = "pitching") {
  
  if (year != 2025) stop("This function is only for the 2025 season.")
  if (!(type %in% c("batting", "pitching", "fielding"))) stop("Type must be 'batting', 'pitching', or 'fielding'.")
  
  season_ids <- list(
    batting = 15687,
    pitching = 15688,
    fielding = 15689
  )
  
  type_id <- season_ids[[type]]
  url <- glue("https://stats.ncaa.org/teams/{team_id}/season_to_date_stats?year_stat_category_id={type_id}")
  
  page <- read_html(url)
  tables <- html_table(page, fill = TRUE)
  
  if (length(tables) == 0) {
    message(glue("No {type} data available for {year}."))
    return(NA)
  }
  
  df <- tables[[1]] %>%
    janitor::clean_names() 
  
  if (type == "pitching"){
    df <- df |>
      mutate(across(c(bf, bb, hb, ibb, sha, sfa, h), as.numeric),
             AB = bf - (bb + hb + ibb + sha + sfa),
             BAA = h/AB)
  }
  
  df <- df %>%
    mutate(across(c(number, player, yr, pos, ht, b_t), ~na_if(., ""))) %>%
    fill(number, player, yr, pos, ht, b_t, .direction = "down")
  
  df$team_id <- team_id
  df$year <- year
  
  df
}

ncaa_2025_player_stats <- function(team_id, year = 2025, type = "pitching", target_player) {
  df <- ncaa_2025_stats(team_id, year, type)
  
  if (is.null(df) || inherits(df, "logical") && length(df) == 1 && is.na(df) || nrow(df) == 0) {
    message("No data available for this team/year/type.")
    return(NA)
  }
  
  # Filter by player name
  df_player <- df %>% 
    filter(grepl(target_player, player, ignore.case = TRUE))
  
  if (nrow(df_player) == 0) {
    message(glue("No stats found for player '{target_player}'."))
    return(NA)
  }
  
  return(df_player)
}

