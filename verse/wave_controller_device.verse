using { /Fortnite.com/Devices }
using { /Fortnite.com/Characters }
using { /Fortnite.com/Playspaces }
using { /Verse.org/Simulation }
using { /UnrealEngine.com/Temporary/Diagnostics }

# 特殊词缀枚举 (7 大核心词缀)
wave_affix := enum:
    None
    Sprinter       # 极速: 移速+100%
    Unstoppable    # 霸体: 免疫击退与控制
    Siege          # 强杀: 锁死拆核心，无视玩家仇恨
    FlankAmbush    # 偷袭: 基地内部/侧翼近身生成
    Enraged        # 狂暴: 残血伤害暴涨
    Volatile       # 自爆: 死后核爆
    FrostAura      # 霜冻: 减速光环

# 出怪路线枚举
incursion_route := enum:
    NorthOnly           # 正北单向
    SouthOnly           # 正南单向
    EastWestPincer      # 东西夹击
    NorthSouthPincer    # 南北对穿
    SurroundAllFour     # 四向合围
    SanctuaryAmbush     # 圣域偷袭

# 单波导演配置结构体
wave_director_config := struct:
    WaveIndex : int
    ThreatBudget : int
    Route : incursion_route
    PrimaryAffix : wave_affix
    SecondaryAffix : wave_affix
    IsBossWave : logic
    IsBonusWave : logic
    CombatDurationSeconds : float = 45.0
    GreedWindowSeconds : float = 45.0

# 波次生成与 Wave Director 动态调度控制器
wave_controller_device := class(creative_device):

    # 关卡核心参数
    @editable MaxWaves : int = 30
    @editable DefaultCombatDuration : float = 45.0
    @editable DefaultGreedWindow : float = 45.0

    # 四向独立出怪阵列 (内部由导演调度，移除 @editable 杜绝 UEFN 反射空元素校验错误)
    var NorthSpawners : []creature_spawner_device = array{}
    var SouthSpawners : []creature_spawner_device = array{}
    var EastSpawners : []creature_spawner_device = array{}
    var WestSpawners : []creature_spawner_device = array{}

    # 特殊首领与狂欢阵列
    var BossSpawners : []creature_spawner_device = array{}
    var BonusSpawners : []creature_spawner_device = array{}

    # HUD 战术广播与 RPG 英雄成长关联
    @editable WaveAnnouncementHud : ?hud_message_device = false
    @editable HeroRpgDevice : ?hero_rpg_device = false

    # 运行时状态
    var CurrentWave : int = 0
    var IsWaveActive : logic = false
    var PlayerCountScaling : float = 1.0

    # 波次事件分发
    WaveStartedEvent<public> : event(int) = event(int){}
    WaveClearedEvent<public> : event(int) = event(int){}
    AllWavesCompletedEvent<public> : event() = event(){}

    OnBegin<override>()<suspends> : void =
        CalculateDynamicScaling()
        DisableAllSpawners()
        Print("【Wave Director】初始化完毕！动态缩放系数: {PlayerCountScaling}")

    # 计算 1~4 人弹性动态平衡系数 Sp
    CalculateDynamicScaling() : void =
        AllPlayers := GetPlayspace().GetPlayers()
        Count := AllPlayers.Length
        if (Count <= 1):
            set PlayerCountScaling = 0.55
        else if (Count = 2):
            set PlayerCountScaling = 0.80
        else if (Count = 3):
            set PlayerCountScaling = 1.00
        else:
            set PlayerCountScaling = 1.25

    # 启动 4 阶段宏观心流主循环: [1.高压防守] -> [2.战场清算] -> [3.贪婪发育] -> [4.警报回防]
    StartWaveSequence<public>()<suspends> : void =
        loop:
            if (CurrentWave >= MaxWaves):
                Print("【最终胜局】零号矩阵解析完毕！虚空之渊被彻底封印！")
                AllWavesCompletedEvent.Signal()
                break

            set CurrentWave += 1
            Config := GetWaveConfig(CurrentWave)

            # -------------------------------------------------------------
            # 阶段 1: 高压防守 (Combat Phase)
            # -------------------------------------------------------------
            set IsWaveActive = true
            BroadcastWaveStart(Config)
            WaveStartedEvent.Signal(CurrentWave)
            EnableRouteSpawners(Config.Route, Config.IsBossWave, Config.IsBonusWave)

            # 战斗持续倒计时
            Sleep(Config.CombatDurationSeconds)

            # -------------------------------------------------------------
            # 阶段 2: 战场清算 (Threat Eradication)
            # -------------------------------------------------------------
            DisableAllSpawners()
            set IsWaveActive = false
            WaveClearedEvent.Signal(CurrentWave)

            # 结算全队战利品 (对标魔兽争霸3《守护雅典娜》波次经验与金币发放)
            if (HeroDevice := HeroRpgDevice?):
                WaveGold := 100 + CurrentWave * 50
                WaveExp := 150 + CurrentWave * 60
                for (Player : GetPlayspace().GetPlayers()):
                    HeroDevice.AwardKillExpAndGold(Player, WaveGold, WaveExp)

            if (CurrentWave >= MaxWaves):
                AllWavesCompletedEvent.Signal()
                break

            # -------------------------------------------------------------
            # 阶段 3: 贪婪发育窗口 (Greed & Growth Window: 45s~60s)
            # -------------------------------------------------------------
            TotalGreedTime := Config.GreedWindowSeconds
            AlarmDuration := 10.0
            MainGreedTime := if (TotalGreedTime > AlarmDuration) then (TotalGreedTime - AlarmDuration) else 5.0

            BroadcastGreedWindow(TotalGreedTime)
            Sleep(MainGreedTime)

            # -------------------------------------------------------------
            # 阶段 4: 紧急警报与回防预警 (Alarm & Recall Window: 10s)
            # -------------------------------------------------------------
            NextWaveIndex := CurrentWave + 1
            NextConfig := GetWaveConfig(NextWaveIndex)
            BroadcastRecallAlarm(AlarmDuration, NextConfig)
            Sleep(AlarmDuration)

    # 查表获取 30 波详细导演配置
    GetWaveConfig(Wave : int) : wave_director_config =
        # 基础威胁预算计算: 20 + (Wave - 1) * 8
        BaseBudget := 20 + (Wave - 1) * 8

        case (Wave):
            # --- 周期 1 (Wave 1~6) ---
            1 => wave_director_config{WaveIndex := 1, ThreatBudget := 20, Route := incursion_route.NorthOnly, PrimaryAffix := wave_affix.None, SecondaryAffix := wave_affix.None, IsBossWave := false, IsBonusWave := false, CombatDurationSeconds := 40.0, GreedWindowSeconds := 45.0}
            2 => wave_director_config{WaveIndex := 2, ThreatBudget := 28, Route := incursion_route.SouthOnly, PrimaryAffix := wave_affix.None, SecondaryAffix := wave_affix.None, IsBossWave := false, IsBonusWave := false, CombatDurationSeconds := 40.0, GreedWindowSeconds := 45.0}
            3 => wave_director_config{WaveIndex := 3, ThreatBudget := 36, Route := incursion_route.EastWestPincer, PrimaryAffix := wave_affix.Sprinter, SecondaryAffix := wave_affix.None, IsBossWave := false, IsBonusWave := false, CombatDurationSeconds := 45.0, GreedWindowSeconds := 45.0}
            4 => wave_director_config{WaveIndex := 4, ThreatBudget := 44, Route := incursion_route.NorthSouthPincer, PrimaryAffix := wave_affix.None, SecondaryAffix := wave_affix.None, IsBossWave := false, IsBonusWave := false, CombatDurationSeconds := 45.0, GreedWindowSeconds := 45.0}
            5 => wave_director_config{WaveIndex := 5, ThreatBudget := 52, Route := incursion_route.EastWestPincer, PrimaryAffix := wave_affix.Unstoppable, SecondaryAffix := wave_affix.None, IsBossWave := false, IsBonusWave := false, CombatDurationSeconds := 45.0, GreedWindowSeconds := 45.0}
            6 => wave_director_config{WaveIndex := 6, ThreatBudget := 110, Route := incursion_route.NorthOnly, PrimaryAffix := wave_affix.Unstoppable, SecondaryAffix := wave_affix.None, IsBossWave := true, IsBonusWave := false, CombatDurationSeconds := 60.0, GreedWindowSeconds := 50.0}

            # --- 周期 2 (Wave 7~12) ---
            7 => wave_director_config{WaveIndex := 7, ThreatBudget := 60, Route := incursion_route.SurroundAllFour, PrimaryAffix := wave_affix.None, SecondaryAffix := wave_affix.None, IsBossWave := false, IsBonusWave := true, CombatDurationSeconds := 40.0, GreedWindowSeconds := 50.0}
            8 => wave_director_config{WaveIndex := 8, ThreatBudget := 68, Route := incursion_route.EastWestPincer, PrimaryAffix := wave_affix.Sprinter, SecondaryAffix := wave_affix.None, IsBossWave := false, IsBonusWave := false, CombatDurationSeconds := 45.0, GreedWindowSeconds := 45.0}
            9 => wave_director_config{WaveIndex := 9, ThreatBudget := 76, Route := incursion_route.SanctuaryAmbush, PrimaryAffix := wave_affix.FlankAmbush, SecondaryAffix := wave_affix.Sprinter, IsBossWave := false, IsBonusWave := false, CombatDurationSeconds := 45.0, GreedWindowSeconds := 45.0}
            10 => wave_director_config{WaveIndex := 10, ThreatBudget := 84, Route := incursion_route.SurroundAllFour, PrimaryAffix := wave_affix.Siege, SecondaryAffix := wave_affix.None, IsBossWave := false, IsBonusWave := false, CombatDurationSeconds := 45.0, GreedWindowSeconds := 45.0}
            11 => wave_director_config{WaveIndex := 11, ThreatBudget := 92, Route := incursion_route.NorthSouthPincer, PrimaryAffix := wave_affix.Volatile, SecondaryAffix := wave_affix.None, IsBossWave := false, IsBonusWave := false, CombatDurationSeconds := 45.0, GreedWindowSeconds := 45.0}
            12 => wave_director_config{WaveIndex := 12, ThreatBudget := 150, Route := incursion_route.SouthOnly, PrimaryAffix := wave_affix.Siege, SecondaryAffix := wave_affix.Unstoppable, IsBossWave := true, IsBonusWave := false, CombatDurationSeconds := 60.0, GreedWindowSeconds := 50.0}

            # --- 周期 3 (Wave 13~18) ---
            13 => wave_director_config{WaveIndex := 13, ThreatBudget := 100, Route := incursion_route.SurroundAllFour, PrimaryAffix := wave_affix.Unstoppable, SecondaryAffix := wave_affix.Enraged, IsBossWave := false, IsBonusWave := false, CombatDurationSeconds := 50.0, GreedWindowSeconds := 45.0}
            14 => wave_director_config{WaveIndex := 14, ThreatBudget := 108, Route := incursion_route.EastWestPincer, PrimaryAffix := wave_affix.FlankAmbush, SecondaryAffix := wave_affix.Siege, IsBossWave := false, IsBonusWave := false, CombatDurationSeconds := 50.0, GreedWindowSeconds := 45.0}
            15 => wave_director_config{WaveIndex := 15, ThreatBudget := 80, Route := incursion_route.SurroundAllFour, PrimaryAffix := wave_affix.None, SecondaryAffix := wave_affix.None, IsBossWave := false, IsBonusWave := true, CombatDurationSeconds := 45.0, GreedWindowSeconds := 55.0}
            16 => wave_director_config{WaveIndex := 16, ThreatBudget := 116, Route := incursion_route.SurroundAllFour, PrimaryAffix := wave_affix.Siege, SecondaryAffix := wave_affix.Sprinter, IsBossWave := false, IsBonusWave := false, CombatDurationSeconds := 50.0, GreedWindowSeconds := 45.0}
            17 => wave_director_config{WaveIndex := 17, ThreatBudget := 124, Route := incursion_route.NorthSouthPincer, PrimaryAffix := wave_affix.FrostAura, SecondaryAffix := wave_affix.Unstoppable, IsBossWave := false, IsBonusWave := false, CombatDurationSeconds := 50.0, GreedWindowSeconds := 45.0}
            18 => wave_director_config{WaveIndex := 18, ThreatBudget := 190, Route := incursion_route.EastWestPincer, PrimaryAffix := wave_affix.Siege, SecondaryAffix := wave_affix.FlankAmbush, IsBossWave := true, IsBonusWave := false, CombatDurationSeconds := 65.0, GreedWindowSeconds := 50.0}

            # --- 周期 4 (Wave 19~24) ---
            19 => wave_director_config{WaveIndex := 19, ThreatBudget := 132, Route := incursion_route.SurroundAllFour, PrimaryAffix := wave_affix.Sprinter, SecondaryAffix := wave_affix.Volatile, IsBossWave := false, IsBonusWave := false, CombatDurationSeconds := 50.0, GreedWindowSeconds := 45.0}
            20 => wave_director_config{WaveIndex := 20, ThreatBudget := 140, Route := incursion_route.EastWestPincer, PrimaryAffix := wave_affix.Siege, SecondaryAffix := wave_affix.Unstoppable, IsBossWave := false, IsBonusWave := false, CombatDurationSeconds := 50.0, GreedWindowSeconds := 45.0}
            21 => wave_director_config{WaveIndex := 21, ThreatBudget := 148, Route := incursion_route.SanctuaryAmbush, PrimaryAffix := wave_affix.FlankAmbush, SecondaryAffix := wave_affix.Volatile, IsBossWave := false, IsBonusWave := false, CombatDurationSeconds := 50.0, GreedWindowSeconds := 45.0}
            22 => wave_director_config{WaveIndex := 22, ThreatBudget := 156, Route := incursion_route.SurroundAllFour, PrimaryAffix := wave_affix.Enraged, SecondaryAffix := wave_affix.Siege, IsBossWave := false, IsBonusWave := false, CombatDurationSeconds := 50.0, GreedWindowSeconds := 45.0}
            23 => wave_director_config{WaveIndex := 23, ThreatBudget := 164, Route := incursion_route.NorthSouthPincer, PrimaryAffix := wave_affix.FrostAura, SecondaryAffix := wave_affix.Enraged, IsBossWave := false, IsBonusWave := false, CombatDurationSeconds := 50.0, GreedWindowSeconds := 45.0}
            24 => wave_director_config{WaveIndex := 24, ThreatBudget := 230, Route := incursion_route.NorthOnly, PrimaryAffix := wave_affix.Unstoppable, SecondaryAffix := wave_affix.Siege, IsBossWave := true, IsBonusWave := false, CombatDurationSeconds := 70.0, GreedWindowSeconds := 50.0}

            # --- 周期 5: 终局狂澜 (Wave 25~30) ---
            25 => wave_director_config{WaveIndex := 25, ThreatBudget := 100, Route := incursion_route.SurroundAllFour, PrimaryAffix := wave_affix.None, SecondaryAffix := wave_affix.None, IsBossWave := false, IsBonusWave := true, CombatDurationSeconds := 45.0, GreedWindowSeconds := 55.0}
            26 => wave_director_config{WaveIndex := 26, ThreatBudget := 180, Route := incursion_route.SurroundAllFour, PrimaryAffix := wave_affix.Siege, SecondaryAffix := wave_affix.Sprinter, IsBossWave := false, IsBonusWave := false, CombatDurationSeconds := 55.0, GreedWindowSeconds := 45.0}
            27 => wave_director_config{WaveIndex := 27, ThreatBudget := 188, Route := incursion_route.SurroundAllFour, PrimaryAffix := wave_affix.FlankAmbush, SecondaryAffix := wave_affix.Unstoppable, IsBossWave := false, IsBonusWave := false, CombatDurationSeconds := 55.0, GreedWindowSeconds := 45.0}
            28 => wave_director_config{WaveIndex := 28, ThreatBudget := 196, Route := incursion_route.SurroundAllFour, PrimaryAffix := wave_affix.Volatile, SecondaryAffix := wave_affix.Siege, IsBossWave := false, IsBonusWave := false, CombatDurationSeconds := 55.0, GreedWindowSeconds := 45.0}
            29 => wave_director_config{WaveIndex := 29, ThreatBudget := 204, Route := incursion_route.SurroundAllFour, PrimaryAffix := wave_affix.Enraged, SecondaryAffix := wave_affix.Unstoppable, IsBossWave := false, IsBonusWave := false, CombatDurationSeconds := 55.0, GreedWindowSeconds := 45.0}
            30 => wave_director_config{WaveIndex := 30, ThreatBudget := 320, Route := incursion_route.SurroundAllFour, PrimaryAffix := wave_affix.Siege, SecondaryAffix := wave_affix.Unstoppable, IsBossWave := true, IsBonusWave := false, CombatDurationSeconds := 90.0, GreedWindowSeconds := 0.0}

            _ => wave_director_config{WaveIndex := Wave, ThreatBudget := BaseBudget, Route := incursion_route.SurroundAllFour, PrimaryAffix := wave_affix.None, SecondaryAffix := wave_affix.None, IsBossWave := false, IsBonusWave := false, CombatDurationSeconds := 45.0, GreedWindowSeconds := 45.0}

    # 根据进攻路线与波次特性精准激活对应生成器
    EnableRouteSpawners(Route : incursion_route, IsBoss : logic, IsBonus : logic) : void =
        case (Route):
            incursion_route.NorthOnly =>
                EnableSpawners(NorthSpawners)
            incursion_route.SouthOnly =>
                EnableSpawners(SouthSpawners)
            incursion_route.EastWestPincer =>
                EnableSpawners(EastSpawners)
                EnableSpawners(WestSpawners)
            incursion_route.NorthSouthPincer =>
                EnableSpawners(NorthSpawners)
                EnableSpawners(SouthSpawners)
            incursion_route.SurroundAllFour =>
                EnableSpawners(NorthSpawners)
                EnableSpawners(SouthSpawners)
                EnableSpawners(EastSpawners)
                EnableSpawners(WestSpawners)
            incursion_route.SanctuaryAmbush =>
                # 偷袭波次: 开启西翼与东翼营地突击
                EnableSpawners(WestSpawners)
                EnableSpawners(EastSpawners)

        # 首领怪额外召唤
        if (IsBoss?):
            EnableSpawners(BossSpawners)

        # 淘金运宝怪额外召唤
        if (IsBonus?):
            EnableSpawners(BonusSpawners)

    EnableSpawners(Spawners : []creature_spawner_device) : void =
        for (Spawner : Spawners):
            Spawner.Enable()

    DisableAllSpawners() : void =
        for (Spawner : NorthSpawners):
            Spawner.Disable()
        for (Spawner : SouthSpawners):
            Spawner.Disable()
        for (Spawner : EastSpawners):
            Spawner.Disable()
        for (Spawner : WestSpawners):
            Spawner.Disable()
        for (Spawner : BossSpawners):
            Spawner.Disable()
        for (Spawner : BonusSpawners):
            Spawner.Disable()

    # 路线与词缀可读文本格式化
    FormatRouteName(Route : incursion_route) : string =
        case (Route):
            incursion_route.NorthOnly => "【正北正面突破】"
            incursion_route.SouthOnly => "【正南防御裂隙】"
            incursion_route.EastWestPincer => "【东西两翼夹击】"
            incursion_route.NorthSouthPincer => "【南北轴心对穿】"
            incursion_route.SurroundAllFour => "【四向全域合围】"
            incursion_route.SanctuaryAmbush => "【高危！暗影折跃偷袭】"

    FormatAffixName(Affix : wave_affix) : string =
        case (Affix):
            wave_affix.None => ""
            wave_affix.Sprinter => "[极速冲锋] "
            wave_affix.Unstoppable => "[霸体免控] "
            wave_affix.Siege => "[强杀拆核心] "
            wave_affix.FlankAmbush => "[侧翼突入] "
            wave_affix.Enraged => "[残血狂暴] "
            wave_affix.Volatile => "[自爆核爆] "
            wave_affix.FrostAura => "[极寒霜冻] "

    FloatToInt(F : float) : int =
        if (Val := Int[F]):
            return Val
        else:
            return 0

    # 阶段 1 广播: 战役高压打响
    BroadcastWaveStart(Config : wave_director_config) : void =
        RouteStr := FormatRouteName(Config.Route)
        Affix1Str := FormatAffixName(Config.PrimaryAffix)
        Affix2Str := FormatAffixName(Config.SecondaryAffix)

        if (Config.IsBossWave?):
            Msg := "【领主降临】第 {Config.WaveIndex} 波！灾厄领主降临！{RouteStr} 词缀: {Affix1Str}{Affix2Str}"
            ShowAnnouncement(Msg)
        else if (Config.IsBonusWave?):
            Msg := "【淘金狂欢】第 {Config.WaveIndex} 波！虚空运宝飞艇全图出现！全员抢金发育！"
            ShowAnnouncement(Msg)
        else:
            Msg := "【怪潮突入】第 {Config.WaveIndex} 波！{RouteStr} 词缀: {Affix1Str}{Affix2Str}誓死保卫核心！"
            ShowAnnouncement(Msg)

    # 阶段 3 广播: 贪婪发育窗口开启
    BroadcastGreedWindow(Duration : float) : void =
        IntSec := FloatToInt(Duration)
        Msg := "【清场完毕·贪婪窗口开启】下一波还有 {IntSec} 秒！抓紧前往西翼折跃门刷金或东翼工坊升级军备！"
        ShowAnnouncement(Msg)

    # 阶段 4 广播: 红色回防警报 (最后 10 秒)
    BroadcastRecallAlarm(RemainingSeconds : float, NextConfig : wave_director_config) : void =
        NextRoute := FormatRouteName(NextConfig.Route)
        NextAffix := FormatAffixName(NextConfig.PrimaryAffix)
        IntSec := FloatToInt(RemainingSeconds)
        Msg := "【紧急警报·全员回防】倒计时 {IntSec} 秒！下一波将从 {NextRoute} 突入！预警词缀: {NextAffix}异界特工速归！"
        ShowAnnouncement(Msg)

    ShowAnnouncement(Text : string) : void =
        Print(Text)
        if (Hud := WaveAnnouncementHud?):
            Hud.SetText(StringToMessage(Text))
            Hud.Show()

    # 外部接口
    GetCurrentWaveIndex<public>()<transacts> : int = CurrentWave
    GetScalingFactor<public>()<transacts> : float = PlayerCountScaling

    StringToMessage<localizes>(Value : string) : message = "{Value}"
