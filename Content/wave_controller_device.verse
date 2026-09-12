using { /Fortnite.com/Devices }
using { /Fortnite.com/Characters }
using { /Fortnite.com/Playspaces }
using { /Verse.org/Simulation }
using { /UnrealEngine.com/Temporary/Diagnostics }

# 波次类型
wave_type := enum:
    Standard        # 标准进攻波次
    EliteBoss       # 精英 Boss 波次 (W10, W20)
    BonusCarnival   # 补给狂欢波 (W15, W25)
    FinalSovereign  # 终局领主波次 (W30)

# 波次生成与怪潮动态调度控制器
wave_controller_device := class(creative_device):

    # 关卡参数
    @editable MaxWaves : int = 30
    @editable WaveDurationSeconds : float = 45.0
    @editable BreakDurationSeconds : float = 20.0

    # 关联装置
    @editable LaneSpawners : []creature_spawner_device = array{}
    @editable BossSpawners : []creature_spawner_device = array{}
    @editable BonusSpawners : []creature_spawner_device = array{}
    @editable WaveAnnouncementHud : ?hud_message_device = false

    # 运行状态
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
        Print("【波次调度器】初始化就绪！人数缩放系数: {PlayerCountScaling}")

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

    # 启动波次主循环
    StartWaveSequence<public>()<suspends> : void =
        loop:
            if (CurrentWave >= MaxWaves):
                Print("【最终胜局】全 30 波怪潮已被彻底抵御！")
                AllWavesCompletedEvent.Signal()
                break

            set CurrentWave += 1
            WaveClass := DetermineWaveType(CurrentWave)

            # 1. 备战阶段倒计时
            ShowAnnouncement("第 {CurrentWave} / {MaxWaves} 波将在 {BreakDurationSeconds} 秒后突入！")
            Sleep(BreakDurationSeconds)

            # 2. 正式进攻阶段
            set IsWaveActive = true
            BroadcastWaveStart(CurrentWave, WaveClass)
            WaveStartedEvent.Signal(CurrentWave)
            EnableWaveSpawners(WaveClass)

            # 3. 进攻时长倒计时
            Sleep(WaveDurationSeconds)

            # 4. 本波结束休整
            DisableAllSpawners()
            set IsWaveActive = false
            ShowAnnouncement("第 {CurrentWave} 波怪潮已被击溃！防线暂时安全！")
            WaveClearedEvent.Signal(CurrentWave)

    # 判定波次类型
    DetermineWaveType(Wave : int) : wave_type =
        if (Wave = 30):
            return wave_type.FinalSovereign
        else if (Wave = 15 or Wave = 25):
            return wave_type.BonusCarnival
        else if (Wave = 10 or Wave = 20):
            return wave_type.EliteBoss
        else:
            return wave_type.Standard

    # 根据波次类型启动对应生成器
    EnableWaveSpawners(Type : wave_type) : void =
        case (Type):
            wave_type.Standard =>
                for (Spawner : LaneSpawners):
                    Spawner.Enable()
            wave_type.EliteBoss =>
                for (Spawner : LaneSpawners):
                    Spawner.Enable()
                for (BossSpawner : BossSpawners):
                    BossSpawner.Enable()
            wave_type.BonusCarnival =>
                for (BonusSpawner : BonusSpawners):
                    BonusSpawner.Enable()
            wave_type.FinalSovereign =>
                for (Spawner : LaneSpawners):
                    Spawner.Enable()
                for (BossSpawner : BossSpawners):
                    BossSpawner.Enable()

    DisableAllSpawners() : void =
        for (Spawner : LaneSpawners):
            Spawner.Disable()
        for (BossSpawner : BossSpawners):
            BossSpawner.Disable()
        for (BonusSpawner : BonusSpawners):
            BonusSpawner.Disable()

    BroadcastWaveStart(Wave : int, Type : wave_type) : void =
        case (Type):
            wave_type.Standard =>
                ShowAnnouncement("【四向突入】第 {Wave} 波敌人正从东、南、西、北四面发起猛攻！誓死捍卫核心！")
            wave_type.EliteBoss =>
                ShowAnnouncement("【领主降临】第 {Wave} 波：高危虚空领主降临！四方怪潮全面压境！")
            wave_type.BonusCarnival =>
                ShowAnnouncement("【淘金狂欢】第 {Wave} 波：虚空运宝队出没！击碎它们打捞巨款！")
            wave_type.FinalSovereign =>
                ShowAnnouncement("【终局裁决】第 30 波：终焉领主·零界裁决者亲临！全员决战！")

    ShowAnnouncement(Text : string) : void =
        Print(Text)
        if (Hud := WaveAnnouncementHud?):
            Hud.SetText(StringToMessage(Text))
            Hud.Show()

    # 外部接口：获取当前波数与缩放
    GetCurrentWaveIndex<public>()<transacts> : int = CurrentWave
    GetScalingFactor<public>()<transacts> : float = PlayerCountScaling

    StringToMessage<localizes>(Value : string) : message = "{Value}"
