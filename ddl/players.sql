CREATE OR REPLACE VIEW mercatool.players AS (

  SELECT
  	r.season,
    r.day,
    r.team,
    r.player,
    r.position,
    r.rating,
    d.played,
    d.grade,
    d.goals,
    d.opponent
  FROM mercatool.ratings r
  LEFT JOIN mercatool.details d
  USING (season, day, team, player)

);
