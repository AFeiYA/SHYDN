using { /Fortnite.com/Devices }
using { /Fortnite.com/Characters }
using { /Fortnite.com/Playspaces }
using { /Verse.org/Simulation }
using { /UnrealEngine.com/Temporary/Diagnostics }

# 四大经典魔兽 RPG 英雄职业
hero_class := enum:
    None
    BladeMaster     # 疾风剑圣: 敏捷刺客 / 极速近战突刺 / 致命顺劈
    DarkRanger      # 黑暗游侠: 敏捷射手 / 远程高频脉冲 / 穿云多重箭
    DemonHunter     # 恶魔猎手: 游击突击 / 双持狂暴冲锋 / 献祭吸血
    Paladin         # 圣殿骑士: 力量重装 / 重型矩阵机枪 / 坚固护盾

# 特工 RPG 运行时数据结构体
player_rpg_profile := class:
    var Class : hero_class = hero_class.None
    var Level : int = 1
    var CurrentExp : int = 0
    var ExpToNext : int = 100
    var Gold : int = 500
    var Kills : int = 0
    var WeaponTier : int = 1
    var HasSelectedHero : logic = false

# 《零界防线》英雄选取与 RPG 属性/神兵成长控制器
hero_rpg_device := class(creative_device):

    # -------------------------------------------------------------
    # 选人神殿按钮与交互装置
    # -------------------------------------------------------------
    @editable BtnSelectBladeMaster : ?button_device = false
    @editable BtnSelectDarkRanger : ?button_device = false
    @editable BtnSelectDemonHunter : ?button_device = false
    @editable BtnSelectPaladin : ?button_device = false

    # 选人后出场折跃门 (折跃至雅典娜外围主防御哨位)
    @editable SpawnArrivalTeleporter : ?teleporter_device = false

    # 全局公告 HUD
    @editable RpgAnnouncementHud : ?hud_message_device = false

    # -------------------------------------------------------------
    # 四大英雄专属神兵阶梯分发器 (Tier 1 ~ Tier 5)
    # -------------------------------------------------------------
    # 1. 疾风剑圣 (Blade Master: 专属近战神刃/近战重喷)
    @editable BM_Granter_T1 : ?item_granter_device = false
    @editable BM_Granter_T2 : ?item_granter_device = false
    @editable BM_Granter_T3 : ?item_granter_device = false
    @editable BM_Granter_T4 : ?item_granter_device = false
    @editable BM_Granter_T5 : ?item_granter_device = false

    # 2. 黑暗游侠 (Dark Ranger: 专属脉冲步枪/穿云重狙)
    @editable DR_Granter_T1 : ?item_granter_device = false
    @editable DR_Granter_T2 : ?item_granter_device = false
    @editable DR_Granter_T3 : ?item_granter_device = false
    @editable DR_Granter_T4 : ?item_granter_device = false
    @editable DR_Granter_T5 : ?item_granter_device = false

    # 3. 恶魔猎手 (Demon Hunter: 专属双持微冲/战术冲锋枪)
    @editable DH_Granter_T1 : ?item_granter_device = false
    @editable DH_Granter_T2 : ?item_granter_device = false
    @editable DH_Granter_T3 : ?item_granter_device = false
    @editable DH_Granter_T4 : ?item_granter_device = false
    @editable DH_Granter_T5 : ?item_granter_device = false

    # 4. 圣殿骑士 (Paladin: 专属重型突击步枪/毁灭重机枪)
    @editable Paladin_Granter_T1 : ?item_granter_device = false
    @editable Paladin_Granter_T2 : ?item_granter_device = false
    @editable Paladin_Granter_T3 : ?item_granter_device = false
    @editable Paladin_Granter_T4 : ?item_granter_device = false
    @editable Paladin_Granter_T5 : ?item_granter_device = false

    # 运行时数据字典
    var PlayerProfiles : [agent]player_rpg_profile = map{}

    # 全局选人事件
    HeroSelectedEvent<public> : event(agent) = event(agent){}
    AllPlayersReadyEvent<public> : event() = event(){}

    OnBegin<override>()<suspends> : void =
        # 绑定选人按钮交互事件
        if (BtnBM := BtnSelectBladeMaster?):
            BtnBM.InteractedWithEvent.Subscribe(OnSelectBladeMaster)
        if (BtnDR := BtnSelectDarkRanger?):
            BtnDR.InteractedWithEvent.Subscribe(OnSelectDarkRanger)
        if (BtnDH := BtnSelectDemonHunter?):
            BtnDH.InteractedWithEvent.Subscribe(OnSelectDemonHunter)
        if (BtnPal := BtnSelectPaladin?):
            BtnPal.InteractedWithEvent.Subscribe(OnSelectPaladin)

        # 注册现有与新加入特工
        for (Player : GetPlayspace().GetPlayers()):
            RegisterPlayer(Player)
        GetPlayspace().PlayerAddedEvent().Subscribe(RegisterPlayer)

        Print("【英雄神殿】英雄选取与 RPG 成长主脑已就绪！")

    RegisterPlayer(Agent : agent) : void =
        if (not PlayerProfiles[Agent]):
            Profile := player_rpg_profile{}
            if (set PlayerProfiles[Agent] = Profile) {}
            Print("【特工接入】已登记特工，等待职业选取。")

    # -------------------------------------------------------------
    # 英雄选取逻辑
    # -------------------------------------------------------------
    OnSelectBladeMaster(Agent : agent) : void =
        AssignHero(Agent, hero_class.BladeMaster, "【疾风剑圣】敏捷刺客")

    OnSelectDarkRanger(Agent : agent) : void =
        AssignHero(Agent, hero_class.DarkRanger, "【黑暗游侠】远程射手")

    OnSelectDemonHunter(Agent : agent) : void =
        AssignHero(Agent, hero_class.DemonHunter, "【恶魔猎手】突击狂暴")

    OnSelectPaladin(Agent : agent) : void =
        AssignHero(Agent, hero_class.Paladin, "【圣殿骑士】重装阵线")

    AssignHero(Agent : agent, Class : hero_class, ClassName : string) : void =
        if (Profile := PlayerProfiles[Agent]):
            if (Profile.HasSelectedHero?):
                Print("特工已经选定职业，不可重复选择！")
                return

            set Profile.Class = Class
            set Profile.HasSelectedHero = true
            Print("特工选定职业: {ClassName}！")

            # 1. 自动配发该职业专属 Tier 1 初始武器并锁定手持第 1 格
            GrantHeroWeapon(Agent, Class, 1)

            # 2. 传送特工离开神殿，入驻雅典娜前线哨位
            if (TeleportToFront := SpawnArrivalTeleporter?):
                TeleportToFront.Teleport(Agent)

            # 3. 广播英雄降临
            HeroSelectedEvent.Signal(Agent)
            CheckAllPlayersReady()

    # 检查是否所有在场特工均已就绪
    CheckAllPlayersReady() : void =
        AllPlayers := GetPlayspace().GetPlayers()
        var AllReady : logic = true
        for (P : AllPlayers):
            if (Profile := PlayerProfiles[P]):
                if (not Profile.HasSelectedHero?):
                    set AllReady = false
            else:
                set AllReady = false

        if (AllReady? and AllPlayers.Length > 0):
            Print("【全员集结】所有特工均已选取英雄！准备启动零界防线！")
            AllPlayersReadyEvent.Signal()

    # -------------------------------------------------------------
    # RPG 经验累加、等级攀升与属性强化
    # -------------------------------------------------------------
    AwardKillExpAndGold<public>(Agent : agent, BountyGold : int, BountyExp : int) : void =
        if (Profile := PlayerProfiles[Agent]):
            set Profile.Gold += BountyGold
            set Profile.CurrentExp += BountyExp
            set Profile.Kills += 1

            Print("【战利品】特工斩获 +{BountyGold}G, +{BountyExp} EXP (总金币: {Profile.Gold}, 经验: {Profile.CurrentExp}/{Profile.ExpToNext})")

            # 升级评估循环
            EvaluateLevelUp(Agent, Profile)

            # 武器自动进阶评估
            EvaluateWeaponUpgrade(Agent, Profile)

    EvaluateLevelUp(Agent : agent, Profile : player_rpg_profile) : void =
        loop:
            if (Profile.CurrentExp >= Profile.ExpToNext and Profile.Level < 30):
                set Profile.CurrentExp -= Profile.ExpToNext
                set Profile.Level += 1
                # 经典经验递增公式: 100 + (Level - 1) * 80
                set Profile.ExpToNext = 100 + (Profile.Level - 1) * 80

                Print("【英雄升级】恭喜特工突破至 Lv.{Profile.Level}！生命与护盾上限提升！")
                
                # 满血回复与基础增益
                if (FortChar := Agent.GetFortCharacter[]):
                    FortChar.SetHealth(100.0)
                    FortChar.SetShield(100.0)
            else:
                break

    # -------------------------------------------------------------
    # 第 1 格本命神兵自动进化 (无需手动跑商店，达到阈值自动换装)
    # -------------------------------------------------------------
    EvaluateWeaponUpgrade(Agent : agent, Profile : player_rpg_profile) : void =
        var TargetTier : int = Profile.WeaponTier

        # 进阶阈值表 (结合等级与累计金币)
        # Tier 2: Lv 4 或 500 金币
        if (Profile.Level >= 4 or Profile.Gold >= 500):
            if (TargetTier < 2):
                set TargetTier = 2

        # Tier 3: Lv 9 或 1500 金币
        if (Profile.Level >= 9 or Profile.Gold >= 1500):
            if (TargetTier < 3):
                set TargetTier = 3

        # Tier 4: Lv 16 或 3500 金币
        if (Profile.Level >= 16 or Profile.Gold >= 3500):
            if (TargetTier < 4):
                set TargetTier = 4

        # Tier 5 (终极神器): Lv 25 或 8000 金币
        if (Profile.Level >= 25 or Profile.Gold >= 8000):
            if (TargetTier < 5):
                set TargetTier = 5

        # 触发神兵进化
        if (TargetTier > Profile.WeaponTier):
            set Profile.WeaponTier = TargetTier
            GrantHeroWeapon(Agent, Profile.Class, TargetTier)
            Print("【神兵觉醒】第 1 格本命神兵突破至 Tier {TargetTier}！")

    # 根据职业与等阶精准分发神兵 (强制装备至主手第 1 格)
    GrantHeroWeapon(Agent : agent, Class : hero_class, Tier : int) : void =
        case (Class):
            hero_class.BladeMaster =>
                case (Tier):
                    1 => if (G := BM_Granter_T1?) { G.GrantItem(Agent) }
                    2 => if (G := BM_Granter_T2?) { G.GrantItem(Agent) }
                    3 => if (G := BM_Granter_T3?) { G.GrantItem(Agent) }
                    4 => if (G := BM_Granter_T4?) { G.GrantItem(Agent) }
                    5 => if (G := BM_Granter_T5?) { G.GrantItem(Agent) }
                    _ => ()
            hero_class.DarkRanger =>
                case (Tier):
                    1 => if (G := DR_Granter_T1?) { G.GrantItem(Agent) }
                    2 => if (G := DR_Granter_T2?) { G.GrantItem(Agent) }
                    3 => if (G := DR_Granter_T3?) { G.GrantItem(Agent) }
                    4 => if (G := DR_Granter_T4?) { G.GrantItem(Agent) }
                    5 => if (G := DR_Granter_T5?) { G.GrantItem(Agent) }
                    _ => ()
            hero_class.DemonHunter =>
                case (Tier):
                    1 => if (G := DH_Granter_T1?) { G.GrantItem(Agent) }
                    2 => if (G := DH_Granter_T2?) { G.GrantItem(Agent) }
                    3 => if (G := DH_Granter_T3?) { G.GrantItem(Agent) }
                    4 => if (G := DH_Granter_T4?) { G.GrantItem(Agent) }
                    5 => if (G := DH_Granter_T5?) { G.GrantItem(Agent) }
                    _ => ()
            hero_class.Paladin =>
                case (Tier):
                    1 => if (G := Paladin_Granter_T1?) { G.GrantItem(Agent) }
                    2 => if (G := Paladin_Granter_T2?) { G.GrantItem(Agent) }
                    3 => if (G := Paladin_Granter_T3?) { G.GrantItem(Agent) }
                    4 => if (G := Paladin_Granter_T4?) { G.GrantItem(Agent) }
                    5 => if (G := Paladin_Granter_T5?) { G.GrantItem(Agent) }
                    _ => ()
            hero_class.None => ()
