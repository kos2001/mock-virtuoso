; Disposable mock scratch cell only: write mode replaces its contents.
let((cv strap net)
  cv = dbOpenCellViewByType("AGENT_EXAMPLES" "PIN_DEMO" "layout" "maskLayout" "w")
  strap = dbCreateRect(cv list("met1" "drawing") list(0:0 4:2))
  net = dbCreateNet(cv "VDD")
  dbCreateTerm(net "VDD" "inputOutput")
  dbCreatePin(net strap)
  dbSave(cv)
  mockInspectCell("AGENT_EXAMPLES" "PIN_DEMO" "layout"))
