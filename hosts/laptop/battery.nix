{
  # Native battery monitoring/action only; no extra collector, timer or GPU query.
  services.upower = {
    enable = true;
    usePercentageForPolicy = true;
    percentageLow = 15;
    # This internal warning level does not initiate Hibernate or notify by itself.
    percentageCritical = 5;
    percentageAction = 2;
    criticalPowerAction = "Hibernate";
  };
}
